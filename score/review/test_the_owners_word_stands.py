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
- test_the_owners_word_stands (the review's accept, reject, waiver, page, web decision and stop line in one tally
  store, and the got-worse judge's rows; folded 2026-11-13 from fourteen tests, each break below applied again
  then and seen red):
    __init__.py: `if judgement is None or (checks.standing(judgement["verdicts"], waived) != checks.PASS and status
    is None):` made `if judgement is None:`; or `gap_objects(verdicts[GAPPED]) <= GAP_OBJECTS` made `True` (a place's
    complete with nine gap objects accepted automatically, shiplock 2026-11-12); or gap_objects' `return
    len({str(finding).split(": ", 1)[0] ...})` made `return len(verdict.get("findings") or ())` (two findings of one
    object counted as two objects)
    __init__.py: `if worse and not worse_reason:` made `if False:`; or `if accepted_record is None: return {}` removed
    (accepted_card: an accepted output with no record here crashes the accept)
    __init__.py: `if allowed_judgement is None or regressions(judgement["verdicts"],
    allowed_judgement["verdicts"]):` made `if allowed_judgement is None:`
    __init__.py: `return moved > 0 and moved >= tolerance(name, new, old)` made `return moved > 0`
    __init__.py: `if checks.ANSWERS.index(new["answer"]) > checks.ANSWERS.index(old["answer"]):` made `if False:`
    __init__.py: `if store.rejected(node, output): return None` made `if False: return None`
    __main__.py: `if not (sys.stdin.isatty() and sys.stdout.isatty()):` made `if False:`
    __init__.py: `waived = store.waivers(node, record["key"]) status` made `waived = {} status`
    __init__.py: `return [line for line in regressions(judgement["verdicts"], card) if line.split(": ", 1)[0] not in
    excused]` made `return regressions(judgement["verdicts"], card)`
    __init__.py: `if current.get("by") == RUNNER else "The owner accepted it"` made `if current.get("by") != RUNNER
    else "The owner accepted it"`
    web.py: `return review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)` made
    `return review.accept(store, node, output, "runner", reason, worse_reason=worse_reason or None)`
    web.py: `if not name or name == RUNNER:` made `if not name:`
    web.py: `return review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)` made
    `return review.accept(store, node, output, name, reason, worse_reason=worse_reason or "his reason")`
    web.py: `name = checked_by(by) baseline` made `name = by baseline`
- test_the_owners_word_stands, its concept draws (folded 2026-11-14 from thirty tests into one store's wordings,
  campgrounds draws, Discusses, clicks and picks and the layers' draws; each break below applied again then and
  seen red):
    concepts.py: `yes = compute.require_cleared("a concept draw", store)` made `yes = {"euros": 0.0, "key":
    "never-cleared"}`
    concepts.py: `return f"{wording} The creator's note: {note.strip()}" if note.strip() else wording` made `return
    wording`
    concepts.py: `if corrected != own_wording(store, place): worded(` made `if False: worded(`
    concepts.py: `if sha is not None and sha not in {draw["sha"] for draw in draws(store, place)}:` made `if False:`
    web.py: `env={**os.environ, "SCORE_SPEND_STORE": str(store.cache.parent)}, stdout=out,` made
    `env={**os.environ}, stdout=out,`
    concepts.py: `except Exception as failed: # any failure of the copy` made `except ValueError as failed: # any
    failure of the copy`
    concepts.py: `"--place", place, "--commit"` made `"--place", "", "--commit"`
    concepts.py: `share = google_spend.TIER_PRICE["batch"] if "batch" in stage.get("basis", "") else 1.0` made
    `share = 1.0`
    web.py: `price = concepts.redraw_euros() if redraw else concepts.draw_euros() if price is None or
    abs(float(euros) - price) > 0.005:` made `price = concepts.redraw_euros() if redraw else concepts.draw_euros()
    if price is None:`
    concepts.py: `if store.is_framework_store() and running_under_agent():` made `if False:`
    concepts.py: `("crop", holder, box))] if box else []` made `("crop", holder, box))] if False else []`
    concepts.py: `if not resolved(ref["picture"]).is_file()]` made `if False]`
    concepts.py: `inputs_of(place).get("says", ""), f"Look:` made `"", f"Look:`
    concepts.py: `words = re.sub(r",? ?(at |about )?\\d+(\\.\\d+)?( ?x ?\\d+(\\.\\d+)?)? ?m\\b", "", words)` made
    `(nothing)`
    concepts.py: `view = INSIDE_VIEW + (ROOF_KEPT if above(place, store) else "") if indoors(store, place) else
    OUTSIDE_VIEW` made `view = OUTSIDE_VIEW`
    concepts.py: `return bool(people_rows.persons(place) or people_rows.crowd_row(place) or
    PEOPLE_WORDS.search(look_text(place)))` made `return True`
    concepts.py: `return any(str(draw.get("wording", "")).startswith(wording)` made `return any(True`
    concepts.py: `sent = checked_wording(request.get("wording")) or wording_now(store, place)` made `sent =
    wording_now(store, place)`
    concepts.py: `"no other doors or openings") if leads else ""` made `"") if leads else ""`
    concepts.py: `for other in joined(store, place) if picked(store, other)]` made `for other in [] if picked(store,
    other)]`
    concepts.py: `ratio = round(own[0] / others[-1])` made `ratio = 1`
    concepts.py: `style(store)) if part)` made `style(store) * 9) if part)`
    concepts.py: `(f" of the picked concept of the {mark['on']}" if "on" in mark else "")` made `""`
    concepts.py: `return f"In the {shell}{side}; for {no_sizes(entry['for'])}."` made `return ""`
    concepts.py: `if holder and not plan_made(store, holder):` made `if False:`
    concepts.py: `if place in tree()["parts"]: return f"is part` made `if False: return f"is part`
    concepts.py: `for number, name in enumerate(listed, 1))` made `for number, name in enumerate(listed, 2))`
    discuss.py: `yes = compute.require_cleared("a concept discussion", store)` made `yes = {"euros": 0.0, "key":
    "never-cleared"}`
    discuss.py: `if entry["base"] == base and entry["at"] > drawn]` made `if entry["base"] == base]`
    web.py: `price = discuss.price() if price is None or abs(float(euros) - price) > 0.005:` made `price =
    discuss.price() if price is None:`
- test_the_owners_word_stands (folded 2026-11-14 into its JUDGED rows; each break applied again then, seen red):
    discuss.py: `return round(google_spend.dollars(concepts.PROMPT_MODEL, usage)` made `return round(100 *
    google_spend.dollars(concepts.PROMPT_MODEL, usage)`
- test_the_owners_word_stands, its environment concept (folded 2026-11-14 from nine tests into one store's lock,
  unlock and lock again; each break below applied again then and seen red):
    environment_concept.py: `if node not in tree["within"] and node not in tree["parts"]` made `if node not in
    tree["within"]`
    environment_concept.py: `return record if "setting" in concept else {` made `return record if True else {`
    concepts.py: `if held is None: return inputs_of(place).get("references", [])` made `if True: return
    inputs_of(place).get("references", [])`
    environment_concept.py: `return bool(found) and not found["locked"]` made `return False`
    environment_concept.py: `if len(found) > LONGEST_LINE:` made `if False:`
    environment_concept.py: `yes = compute.require_cleared("an environment concept ask", store)` made `yes =
    {"euros": 0.0, "key": "never-cleared"}`
    web.py: `price = environment_concept.ask_euros() if price is None or abs(float(euros) - price) > 0.005:` made
    `price = environment_concept.ask_euros() if price is None:`
    environment_concept.py: `if named in index and index[named]["key"] != key:` made `if False:`
    environment_concept.py: `if offsite is None and running_under_agent():` made `if False:`
- test_the_owners_word_stands, its setting and sky (folded 2026-11-13 from fifteen tests on the cited table, a
  setting's shape and the sky overhead, each break below applied again then and seen red):
    data/physics/bodies.json: `"name": "nasa-sun", "radius_km": "nasa-sun",` made `"name": "nasa-sun",`
    setting.py: `/ (body["radius_km"] * 1000.0) ** 2, 3)` made `/ (body["radius_km"] * 1000.0), 3)`
    setting.py: `if shape not in SHAPES:` made `if False:`
    setting.py: `float(str(value).replace(",", "."))` made `float(str(value))`
    setting.py: `if bodies and sum(1 for body in bodies if not body.get("around")) != 1:` made `if False:`
    setting.py: `if row.get("reference") else row` made `if False else row`
    setting.py: `kept = [earlier[site.get("place")] if count[spot(site)] > 1` made `kept =
    [earlier[site.get("place")] if False`
    overhead.py: `lit = (1.0 + float(np.dot(to_light, unit(-toward)))) / 2.0` made `lit = (1.0 -
    float(np.dot(to_light, unit(-toward)))) / 2.0`
    overhead.py: `math.degrees(math.atan2(east, north)) % 360.0` made `math.degrees(math.atan2(north, east)) %
    360.0`
    overhead.py: `"across": round(math.degrees(2.0 * math.asin(star["radius_km"] / apart)), 5)` made `"across":
    round(math.degrees(2.0 * math.asin(star["radius_km"] / 1.496e8)), 5)`
    overhead.py: `if body.get("locked_to"): pole = orbit_pole(body, day)` made `if False: pole = orbit_pole(body,
    day)`
    overhead.py: `lux = star["lux"] * (star["lux_at_km"] / apart) ** 2` made `lux = star["lux"] * (star["lux_at_km"]
    / apart)`
    overhead.py: `if other["body"] == on or other.get("lux") is not None:` made `if other.get("lux") is not None:`
    overhead.py: `hour = 2.0 * math.pi * since / (light["day_hours"] / 24.0)` made `hour = 0.0`
    overhead.py: `360.0 * 24.0 / body["day_hours"]` made `360.0 * 24.0 / 24.0`
- test_the_owners_word_stands, its reading's agreement and schema and its plan's gaps (folded 2026-11-14 from
  eight tests into the AGREED, READ_ANSWERS and GAP_WORDS rows, each break below applied again then and seen red):
    reading.py: `else row for row in rows if structural(row) or row["boxes"]]` made `else row for row in rows if
    row["boxes"]]`
    reading.py: `and area(region) >= LARGE * size[0] * size[1]` made `and area(region) >= 0`
    reading.py: `and head(other) == head(row) and overlapping(other, row, size)), None)` made `and False), None)`
    reading.py: `wrong += [] if row.get("kind") in KINDS else ["kind"]` made `wrong += []`
    reading.py: `raise concepts.Refused(str(unfinished)) from unfinished` made `return ""`
    plan_checks.py: `for first, second, axis, said, drawn in relations(seen, laid, turn) if said != drawn]` made
    `for first, second, axis, said, drawn in relations(seen, laid, turn) if False]`
    plan_checks.py: `if count > 1 and things and item[3] * item[4] > max(SPREAD * things, things + SPREAD_SLACK):`
    made `if False:`
    plan_checks.py: `gaps, left_out = [], beyond(plan, inventory) | people(inventory)` made `gaps, left_out = [],
    people(inventory)`
- test_the_owners_word_stands, its environment plan and kept sky (folded 2026-11-14 from seventeen tests into
  one case table of settings and plans fed through environment_plan.derived, one written then edited plan and one
  timed house; each break below applied again then and seen red):
    environment_plan.py: `return round(max(tops, default=0.0), 2)` made `return 0.0`
    environment_plan.py: `("plan yet", "size" in site and site["size"] is None))` made `("plan yet", False))`
    environment_plan.py: `sites = cleared(sites, radius, pinned)` made `sites = list(sites)`
    environment_plan.py: `if mover["place"] in pinned: still, mover = mover, still` made `if False: still, mover =
    mover, still`
    environment_plan.py: `"x": round(float(still.get("x") or 0.0) + toward[0] * metres, 2)` made `"x":
    round(float(still.get("x") or 0.0) + toward[0] * metres * 2, 2)`
    environment_plan.py: `for site in setting["sites"] if site["on"] == key]` made `for site in setting["sites"]]`;
    and `if placed.get(site["place"], {}).get("on") != world["on"]: continue` made `if False: continue`
    environment_plan.py: `"metres": round(radius * great_angle(one, two) if radius else` made `"metres":
    round(radius * great_angle(one, two) / 2 if radius else`
    environment_plan.py: `found["terrain"] = {"spots": fixed["terrain"]["spots"] + [spot for spot in spots if
    spot[:2] != [0.0, 0.0]]}` made `found["terrain"] = {"spots": fixed["terrain"]["spots"]}`
    environment_plan.py: `shape = from_plan(site_plan(store, site["place"])) if store is not None else {}` made
    `shape = {}`
    environment_plan.py: `sites.append({**site, "time": moment(his["time"]), "written_time": None} if
    his.get("time") else site)` made `sites.append(site)`
    environment_plan.py: `if not (light and light["scene"]["daylight"]) or sun_up(setting, site, written) is not
    False:` made `if True:`
    environment_plan.py: `return found.get("method") == METHOD and found.get("environment") ==
    concept_version(store)` made `return found.get("method") == METHOD`
    environment_plan.py: `round(-(far * far) / (2 * radius), 4) if radius else 0.0` made `round(-(far * far) / (2 *
    radius), 4) if radius else -1.0`
    environment_plan.py: `plan_writing.cleared(store, [f"environment-{world}"]` made `plan_writing.cleared(store,
    [world]`
    environment_plan.py: `if found["metres"] < SAME_SPOT]` made `if found["metres"] < 0]`
    scene_sky.py: `if site["place"] == top and site.get("time"):` made `if site["place"] == place and
    site.get("time"):`
    scene_sky.py: `elif before is not None: path.unlink()` made `elif False: path.unlink()`
- test_the_owners_word_stands (folded 2026-11-14 into its JUDGED rows; each break applied again then, seen red):
    environment_plan.py: `fixed[axis]) + CLEAR_M)` made `fixed[axis]))`
- test_the_owners_word_stands, its picked place's reading (folded 2026-11-14 from ten tests into one store's wreck,
  dock, hull and shack read, parted, lit, read again and fixed; each break below applied again then, seen red):
    reading.py: `{**row, "count": len(row["boxes"]), "box": row["boxes"][0]}` made `{**row, "box": row["boxes"][0]}`
    reading.py: `if sha and found["concept"] == sha and found.get("method")` made `if found.get("method")`
    reading.py: `again = {place: asked_again(store, place, folder) for place in places if earlier_rows(store,
    place)}` made `again = {}`
    reading.py: `refused = {place: answer for place, answer in asked_places.items() if isinstance(answer[0], str)}`
    made `refused = {}`
    reading.py: `and (any("part" not in row for row in found["inventory"]["rows"]) or not parts_current(store,
    found))]` made `and (not parts_current(store, found))]`
    reading.py: `again = None if record.get("parts_version", 1) >= PARTS_VERSION else asked_parts_of(store, record,
    current=True)` made `again = None`
    reading.py: `wrong += ["scene"] if scene["unseen"] and not COLOUR.fullmatch(str(scene["unseen_colour"])) else
    []` made `wrong += []`
    reading.py: `if again else unlit(store, places)` made `if False else unlit(store, places)`
    reading.py: `{"text": LIGHT_ASKED.read_text().format(` made `{"text": WORDS.format(`, the file's words put back
    in reading.py as `WORDS` (the words in code again)
    reading_fixes.py: `rows = reading.reanchored([dict(row) for row in rows], {item["row"]: f"on:{item['into']}" for
    item in merged})` made `rows = [dict(row) for row in rows]`; `rows, added = seats_added(rows)` made `added = {}`
    (the crew left on the floor, no bench)
- test_the_owners_word_stands (folded 2026-11-14 into its JUDGED rows; each break applied again then, seen red):
    reading_fixes.py: `INSIDE = 0.9` made `INSIDE = 0.5`; `if len(named) == 1 and` made `if named and` (a sitter
    on "a stool" anchored on one of two); `people_rows.seat_of(` made `bool(` (anchored on the table);
    `if row["id"] in people and said and not people_rows.seat_of(row)` made `if row["id"] in people and said` (a
    stool added under the pilot already seated); `and not any(` made `and not all(` (a third stool beside the two named);
    `round(tall * SEAT_SHARE * BACKED.get(seat, 1.0), 3)` made `round(tall, 3)` (a bench as tall as its sitter)
- test_the_owners_word_stands, its plan review (folded 2026-11-14 from nine tests into one store's yard and
  shed picked, written, edited, corrected and unpicked, a hut and a farm added; each break below applied again
  then, seen red):
    plans.py: `tied[name] = [row_id, *riders.get(row_id, [])]` made `tied[name] = [row_id]`
    plans.py: `if len(doors) != len(base):` made `if False:`
    plans.py: `float(plan.get("w") or 6.0)` made `float(plan.get("w") or 5.0)`
    plans.py: `return shown is not None and shown["how"] != "derived"` made `return shown is not None`
    plans.py: `if design_done(store, place): kept_for_stage(store, place, record["plan"])` made `if False:
    kept_for_stage(store, place, record["plan"])`
    plans.py: `elif path.is_file(): path.unlink()` made `elif False: path.unlink()`
    plans.py (2026-11-09): kept_for_stage's `if path == KEPT / f"{place}.json" and lays_the_same(path, plan):
    continue` dropped, or laid_of's `if key not in NOTES` made `if True` (a notes-only change rewrites the kept plan);
    lays_the_same's `return path.is_file() and ...` made `return path.is_file()` (a moved thing kept as it was);
    said_once's `list(dict.fromkeys(fixes))` made `list(fixes)` (a fix said twice shown twice)
    plans.py: `yes = compute.require_cleared("a plan correction", store)` made `yes = {"euros": 0.0, "key":
    "never-cleared"}`
    plans.py: `if note or request.get("marks") or request.get("context_marks"): return note` made `if True: return
    note`
    plans.py: `return (round(max(x + size[0] for (x, _), size in zip(spots, sizes)) + GAP, 3),` made `return
    (round(max(x + size[0] for (x, _), size in zip(spots, sizes)), 3),`
- test_the_owners_word_stands, its yard's rooms (folded 2026-11-14 from seven tests, his inside places and rows, a
  room adjoining a row's rooms, a room changed on the holder's plan, a parent rewritten over locked rooms, overlapped
  rooms and things in a room, a reading's boxes as holders' and items sized and ordered by their reading, into one
  store's yard read, written, redrawn and edited round the shed's locks; each break below applied again then, seen
  red):
    plans.py: `within.update({hold["place"]: holder for hold in edit["plan"]["holds"]})` made `within.update({})`
    plans.py: `holds = [{**hold, "row": neighbours_row(hold, holds)} for hold in holds]` made `holds = list(holds)`
    plans.py: moved_draws' `return drawn != room_at(room, size) and not (mine and drawn == room_at(own_room(store,
    place), size))` made `return False` (re-pointed 2026-11-14: the old `return room_at(draw["room"], size) !=
    room_at(room, size)` line is gone)
    plans.py: `return {"plan": locked_rooms_kept(store, place, plan), "how": "written"` made `return {"plan": plan,
    "how": "written"`; plans.py `own_edit`: `and record.get("how") != "redrawn"` dropped (a redrawing unlocks a lock
    drawn before rooms were recorded); `moved`: `and not (mine and drawn == room_at(own_room(store, place), size))`
    dropped (a redrawing unlocks a lock on a recorded room); `his_since = edit["at"] if edit else since` made
    `his_since = since` (a redrawing after his lock unlocks it)
    plans.py: checked_hold's `**({"name": name} if name else {}), **({"things": things} if things else {}),` dropped
    (re-pointed 2026-11-14: the return now also carries checked_instance)
    plans.py: `box = (row.get("boxes") or [None])[0] if "boxes" in row else row.get("box")` made `box =
    row.get("box")`
    plans.py: `instances = sorted(row_items(rows), key=lambda instance: across(instance[3]))` made `instances =
    row_items(rows)`
- test_the_owners_word_stands, its plan review's held spots (folded 2026-11-14, see below):
    plans.py: `if size and (abs(size[0] - hold["w"]) > 0.001 or abs(size[1] - hold["d"]) > 0.001):` made `if False:`
- test_the_owners_word_stands (folded 2026-11-14 into its GAP_WORDS rows; each break applied again then, seen red):
    plan_checks.py: `if (mask & other_mask).sum() > OVERLAP * min(mask.sum(), other_mask.sum())]` made `if False]`
- test_the_owners_word_stands (folded 2026-11-14 into its GAP_WORDS and its stair core's rows; each break applied again then, seen red):
    plan_checks.py: stair_gaps' `if slope > STEEPEST:` made `if False:`
    plan_writing.py: fits' `return not any(plan_checks.too_close(samples, share, low, high, other) for other in laid)`
    made `return True`
- test_the_owners_word_stands, its plan review's held spots (folded 2026-11-14, see below):
    plan_drawing.py (2026-11-04, #72): OUTLINE's "not its shape" wording made "draw this place filling exactly that
    box's shape"
    plan_drawing.py (2026-11-04): `outline=(OUTLINE + ("" if inside else OPEN))` made `outline=OUTLINE`, or ASKED's
    open-ground outline sentence dropped
    concepts.py (2026-11-04): keys_under's `root / prefix.rpartition("/")[0]` made `root / prefix`
    plan_checks.py (2026-11-05, #72): shape_gaps' `if not held or held.get("fitted") or shape_off(plan["w"],
    plan["d"], held) <= SHAPE_SLACK:` made `if True:`
    plan_writing.py (2026-11-05, #72): fitted's `found = turned_quarter(plan) if turn else plan` made `found = plan`,
    or mapped's item_of `middle = at([x + wide / 2, y + deep / 2])` made `middle = at([x, y])`
    plan_drawing.py (2026-11-05, #72): `OPEN + strip_of(place)` made `OPEN`
    plans_pass.py (2026-11-05, #87): laid_again's `stairs, levels = plan_writing.flights_laid(answer)` made `stairs,
    levels = answer.get("stairs") or [], answer.get("levels") or []`
    plans.py (2026-11-05, #72): newest_edit's `and found[-1].get("plan") is not None` dropped
    plans.py (2026-11-05, #72): doors_met's `step = (pair["there"] - pair["spot"]) * (1 if mover == name else -1)` made
    `* (1 if mover != name else -1)`, or `if overlap(box, sibling): box = pushed_out(box, sibling)` dropped, or mover_of's `if not
    by_place[place].get("row")` made `if True`
    plans.py (2026-11-05, #72): current's `edit_inside(store, place, ...)` dropped (the edit shown as made)
    plan_fixes.py (2026-11-06): doors_sized's `found[1]["wide"] = metres` made `pass` (an edit's 0.237 m hatch shown
    for its 2.2 m row)
- test_the_owners_word_stands (folded 2026-11-14 into its JUDGED rows; each break applied again then, seen red):
    plan_writing.py: `keys[0]: left + wide / 2 if middle else left` made `keys[0]: left`
    plan_writing.py (2026-11-03, #72): `found = rows_scale(answer, inventory)` moved under the held branch's return
    of its box each way (`(skeleton["w"] / (extent[2] - extent[0]), skeleton["d"] / (extent[3] - extent[1]))`), and
    `skeleton = {**skeleton, "w": wide, "d": deep, ...}` made `if not held:` only; `doors_along` returning the
    skeleton's doors as they are
- test_the_owners_word_stands, its plan writing (folded 2026-11-14 from four tests, the shed's writing, a writing
  only inside his yes with the flag off, his click asking none with it on and a read place owed unless refused, into
  one store's shed, hut and yard written; each break below applied again then and seen red):
    plan_writing.py: `if row_id not in placed and parent in placed:` made `if False:`
    plan_writing.py: roof_of's `**({"openings": openings} if openings else {})` made `**{}` (a roof's opening dropped:
    the hangar's roof door never cut, 2026-11-04)
    plan_writing.py (2026-11-04, #72): write_now's `if again else to_write(store, places)` made `to_write(...)` alone
    plan_writing.py: `if AUTOMATIC: return compute.spending(` made `if True: return compute.spending(`
    web.py: `if not plan_writing.AUTOMATIC: price = plan_writing.price(store)` made `if True: price =
    plan_writing.price(store)`
    plan_writing.py: `return [place for place in to_write(store, places) if not refused_now(store, place)]` made
    `return to_write(store, places)`
- test_the_owners_word_stands, its FIXED rows (folded 2026-11-14 from four tests, a thing the creator planned, a
  scene added in the app's doors, a missing thing piled on one of its row and a box drawn apart split, into one table
  of the plan writer's fixes, each answer and the plan it leaves read through the same `holds`; each break below
  applied again then and seen red):
    plan_writing.py: `middle = [x + wide / 2, y + deep / 2] if facing is None:` made `middle = [x, y] if facing is
    None:`
    plan_writing.py: `to = holder if opening.get("to") == place else opening.get("to")` made `to =
    opening.get("to")`
    plan_fixes.py: `            if base:` made `            if False:`; or `default=0.0) if piles(row) else 0.0` made
    `default=0.0)`
    plan_fixes.py: `for spot in spots: added_item(plan, row["id"], spot, size, shape)` made `for spot in spots[:1]:`
- test_the_owners_word_stands, its FIXED rows of the free fixes (folded 2026-11-14 from the free fixes' own test into
  rows of the same table, a plan of its own a fix, what it answers, the plan it leaves and what it answers given that
  plan again; each break below applied again then and seen red):
    plan_fixes.py: `plan["people"] = stood + found` made `plan["people"] = found + stood`
    plan_fixes.py: `opening.update(wide=metres, **({"to": lead} if lead is not None else {}))` ->
    `pass`
    plan_fixes.py: `left.remove(spare)` -> `pass` (the moved doorway kept on its drawn wall)
    plan_fixes.py: `lead = (leads.get(f"{key}:{float(door[1]):g}") if sided else None) or (` ->
    `lead = (None) or (` (two doors on one wall lead where its side's one lead does)
    plan_fixes.py: `float(pair[1]["at"][0 if place in ("N", "S") else 1]) - float(along)))` ->
    `0.0))` (a wall's first doorway taken by its first door row, wherever along it stands)
    plan_checks.py: `for item in plan.get("items", []):  # every row tied to an item` loop ->
    placed_items' floor rows alone
    plan_fixes.py `runs_kept_clear`: `box = trimmed(box, blocker, along) if crosses else
    shifted(box, blocker, along)` -> `box = shifted(box, blocker, along)`, or `shape["count"] = kept` dropped,
    or its `count_said(plan, row, ...)` dropped (the cut bags a count gap again, placed back as missing)
    plan_fixes.py `run_doubles_dropped`: `abs(float((run_shape or {}).get("base") or 0.0) - base) <
    1e-3 and` dropped (the bag piled on the run taken off), or `> plan_checks.OVERLAP * item[3] * item[4]` ->
    `> 0` (the bag touching the run's end taken off)
    plan_fixes.py `wall_runs_parted`: `if kept < count:` -> `if False:` (the cut pipe unsaid)
    plan_fixes.py `laid_of`: `int((plan.get("shapes", {}).get(item[0]) or {}).get("count") or 1)`
    -> `1` (the record lays one bag a run)
    plan_fixes.py `walls_and_stairs`: `for stair in plan.get("stairs") or []:` ->
    `for stair in []:` (BAGS 3 left on the ramp)
    plan_fixes.py `nudged`: `others += [box for box in standing_low(plan, inventory, mover) if
    box != still[1:5]] + clear` -> `others += clear` (the box nudged into the suit)
    plan_fixes.py `piled_on_own`: `piles(rows[row])` -> `False` (the sandbag pile stood on the
    floor), or `on_floor[row] not in plan_checks.FLOOR_ANCHORS` dropped (frame 2 taken off its wall)
    plan_fixes.py `floored`: `dict(row, anchor="floor")` -> `row` (RAIL 2 left 1 m up)
    plan_fixes.py `unpiled`: `surplus.append(item)` -> `pass` (the boxed-in stove grounded in
    its first), or `size = [side + 2 * (MARGIN + grid.size) ...]` -> `item[3:5]` (STOVE 2 touching the fridge)
    plan_fixes.py `surplus_dropped`: `plan.setdefault("dropped", []).append(...)` dropped (the
    stove row's count a gap again)
    plan_fixes.py `projector`: `if matrix is None or float(numpy.linalg.norm(...).max()) <
    SPREAD_LEAST:` -> `if matrix is None:` (every box sent to the room's middle)
    plan_fixes.py `flights_cleared`: `if into is None or plan_checks.inside(corners, ...` ->
    `if into is None:` (the lander's ramp moved off its lander), or `made_things`' outline test dropped (the
    stair moved for the 30 m tower), or `made_outline`'s `max(float(wide), item[3])` -> `item[3]` (no ramp moved)
    plans_pass.py `unsettled`: `or bool(plan_fixes.kept_apart(copy.deepcopy(plan), inventory))`
    dropped, or settled_again's `apart = plan_fixes.kept_apart(answer, inventory)` -> `apart = []`
    plan_fixes.py `piled_on_own`: `if under and min(under) < plan_checks.LOW:` -> `if under:`
    (the overhead string 2 brought down to string 1's 6 m and moved)
    plan_fixes.py `wall_runs_parted`: the height band test dropped (PIPE 3 cut into PIPE 1's), or
    `other_row != row` dropped (the panel cut off the pipes), or `continue  # no run` dropped (the panel cut)
    plan_fixes.py `standing_low`: `left_out |= {... holders.holder_kind(row) is not None}`
    dropped (the room-sized wall panel blocks every nudge)
    plan_fixes.py `wall_runs_spread`: `{other[1] for other in runs}` -> `set()` (PIPE 2 laid on
    PIPE 1's own north wall, still in it), or `any(in_each_other(run, other) for other in kept) and` dropped
    (PIPE 1 and the lone south pipe moved too)
    plan_fixes.py `in_each_other`: `and run[4] < other[5] and other[4] < run[5]` dropped (the pipe
    3 m up moved off the north wall)
    plan_fixes.py `wall_runs`: `int(shape.get("count") or 1) > 1 or` dropped (the counted run
    moved), or `holders.spans(rows[row]) or` dropped (the crane moved)
    plan_fixes.py `open_gaps`: `+ stack_gaps(plan, inventory)` dropped (the stacked pipes with
    no gap)
    plan_fixes.py `wall_runs_spread`: `surplus.append(run[0])` -> `pass` (PIPE 5 left in PIPE 1),
    or `continue` after it dropped (PIPE 5 kept beside its drop), or `fixes += surplus_dropped(...)` dropped
    plan_fixes.py `off_flights`: `if laid_of(plan, row) - len(surplus.get(row, [])) > 1:` ->
    `if True:` (a row's last bed taken off), or `-> if False:` (BED 1 left on the stairs beside BED 2)
    plan_fixes.py `surplus_dropped`: `return fixes + resting_dropped(...)` -> `return fixes` (POT
    1 left 0.5 m up where BED 1 went); `resting_dropped`: its `laid_of(...) - ... > 1` -> `True` (the pot row's
    last taken off)
    plan_fixes.py `eaves_raised`: `>= plan_checks.LOW` -> `>= 0.0` (the tube's vault on its
    floor raised), or `roof["top"] = round(...)` dropped (the dome's rise lost)
    plan_fixes.py `stair_rows_dropped`: the `any(other.get("anchor") == ...)` test dropped (the
    staircase its railing stands on taken off), or `if not flights: return []` -> `if False:` (stairs taken off a
    plan with no flights)
    plan_fixes.py `on_flights`: `and not any(crossing(drawn, points) ...)` dropped (the ramp's
    cart moved), or `plan_checks.inside(made, outline).all() and` dropped (the hall made past the plan moved)
    plan_fixes.py `off_flights`: `| ~level` dropped (the chair laid off its level)
    plan_fixes.py `ramps_walled`: `if plan_checks.past_walls(...)` -> `if True:` (the ramp clear of
    the walls taken off) or `if False:` (the ramp laid through the wall kept)
    plan_fixes.py `runs_laid_out`: `range(count, 0, -1)` -> `range(1, 0, -1)` (BAGS 1 cut to one),
    the drawn box's `taken & standing.under(...)` test -> `False` (BAGS 1 left in the suit), or its
    `count_said(...)` dropped (the cut bags unsaid); `run_room`'s off-outline room -> `pass` (BAGS 4 pulled
    inside); `taken_floor`'s `laid_polygon(...)` -> `plan_checks.polygon_of(other, shape)` (the bags left where
    the holders lay the ramp)
    plan_fixes.py `hung_runs`: `long >= RUN_SHARE * short and` dropped (the hung lamps moved to a
    wall), or `hung_runs_laid_out`'s `item[1:5] = first` -> `pass` (the cables left in one another)
    plan_fixes.py `tops_cut`: `if used + needs <= long + 1e-9 or not kept:` -> `if True:` (five
    0.5 m monitors kept on a 2 m desk), or -> `if not kept:` (three that fit cut to one)
- test_the_owners_word_stands, its FIXED rows of a Correct kept or not and a row brought in from beyond (folded
  2026-11-14 from two tests into rows of the same table: the shed's and the hut's stand-in Corrects, the airlock's
  sandbags at the concept's foot, lab's people on spots inside, stairwell's unstood man, the hangar's spread workers
  and the garage's things past its outline; each break below applied again then and seen red):
    plan_fixes.py: `if len(open_gaps(answer, inventory)) >= len(left): break` made `if False: break`
    plan_fixes.py: `plan["beyond"] = [row for row in plan.get("beyond", []) if row in kept]` made `plan["beyond"] =
    plan.get("beyond", [])`
    plans_pass.py: `if plan_checks.inside(numpy.asarray(points, dtype=float), outline).all()]` made `if False]`
    plans_pass.py: `return [row["id"] for row in plan_checks.person_rows(inventory) if row["id"] not in have]` made
    `return []`
    plans_pass.py `stood_again`: `+ spread_people(answer, inventory)` dropped (the hangar's workers stand on no spot)
    plan_fixes.py `items_inside`: `clipped = [min(box[2], outer[2]), min(box[3], outer[3])]` made `clipped =
    box[2:]` (the facade left past the wall)
    plan_fixes.py `people_inside`: `walls_things | ~inside` made `walls_things` (its footprint past the outline)
    plan_fixes.py `moved_inside`: its clamp dropped (`x, y = box[:2]`) (the facade left past the wall)
    plan_fixes.py `frame_inside`: `plan.pop("frame")` dropped
    plans_pass.py `unsettled`: the `plan_fixes.kept_inside` line dropped
- the sync pass's plans keep in test_the_owners_word_stands (folded 2026-11-14 from the narrow walk, the keep in one
  moment, a plan fixed before a fix it needs, a pile parted, an accepted row never parted, a plan placing more, a
  Correct's copies of a person and a done place with no kept plan: one store's habitat, airlock, galley, hold, plaza,
  bay and lock driven through plans_pass.main; each break below applied again then, at today's code, seen red):
    (narrow walk) plans_pass.py: `if path.is_file() and not path.name.endswith(".partial")` made `if path.is_file()`
    (one moment) plans_pass.py: `with plans.one_moment():` made `with contextlib.nullcontext():`
    (the plaza, fixed before a fix it needs) plans_pass.py: `return bool(lacking) and len(missing(plan_fixes.fixed(
    plan, inventory)[0], inventory)) < lacking` made `return False`
    (the airlock's pile) plans_pass.py (settled_again): `if more or spaced or stood` made `if spaced or stood`
    (an accepted row never parted, the bay's bag before the keep) plans_pass.py: `return store.accepted(
    f"plan@{place}") is None` made `return True`; (parted_first) `or not unsettled(` made `or not parting(store,
    place) or not unsettled(` (an accepted row's free re-fix kept a pass later; the lock's spacing too);
    (settled_again) `if doors or within or apart:` made `if False:` (a person left in what kept_apart moved)
    (the galley and hold, placing more) plans_pass.py (settled_again): `relation_solver.parted(plan, inventory) if
    parts else (plan, [])` made `... if True else ...`
    (the lock's copies of a person) plans_pass.py `unnumbered`: `elif row and placed[row["id"]] < int(row.get("count",
    1) or 1):` made `elif row:` (a copy by row kept); `elif row or any(standing.in_each_other(...) ...):` made
    `elif row:` (the copies by position kept); `spots.append([*spot[:3], row["id"]])` made `spots.append(spot)` (no
    row given back); plans.py (people_moved_out) `standing.blocked(plan, shell_floored(plan, inventory), grid,
    sits_on)` made `standing.blocked(plan, inventory, grid, sits_on)` (the spot in the crate on the shell's deck
    kept); standing.py `in_each_other`: `< (size[0] + other_size[0]) / 2` made `< (size[0] + other_size[0]) / 2 +
    0.2` (the near spot moved); standing.py `stands_in`: `bool((walls_things & under(grid, spot, size)).any()) or`
    dropped (the spot in the wall kept); plans_pass.py (unsettled) `or bool(spaced_people(plan, inventory)[1])`
    dropped; plans.py (people_moved_out) `< STILL_M` made `< 0` (a spot the free search hands back where it stands
    logs a 0.00 m move every pass)
    (a done place with no kept plan) plans_pass.py: `if not (plans.KEPT / f"{place}.json").is_file()` made `if True`
- test_the_owners_word_stands, its plan review's held spots (folded 2026-11-14 from
  test_a_spot_takes_its_child_scenes_own_plan_size_centred_where_it_sat_and_says_so into the plan review's store:
  the yard he edits to 30 m round its held shed, the shed locked again with his edits back and written 4 x 10 m, the
  pure judging as HELD_SPOTS' rows; each break below applied again then and seen red):
    Owner, 2026-10-25 ("the framework should be able to solve [it] agnosticly"): a child scene's own plan is drawn
    from its own concept at its own scale, the holder's spot says where it sits; they agree before any paid work.
    Break: score/review/plans.py: `return laid_size(hold, found) if found and found.get("w") else None` ->
        `return (found["w"], found["d"]) if found and found.get("w") else None`
    Break: score/review/plans.py: `by_place = {name_of(hold): dict(hold) for hold in holds}` ->
        `by_place = {hold["place"]: dict(hold) for hold in holds}`
    Break: score/review/plans.py: `if turn >= 360.0:` -> `if False:`
    Break: score/review/plans.py: `if mark and not re.fullmatch(spot, rest):` -> `if False:`
    A hold turned 45 degrees takes its plan's box turned, and two holds overlap only where their outlines do, never
    where only their boxes do (#72: the base's tubes off the hub's diagonal facets).
    Break: score/review/plans.py: `return outlines_overlap(laid_outline(hold, plan), laid_outline(other, other_plan))` ->
        `return outlines_overlap(laid_outline(hold), laid_outline(other, other_plan))`
    The free checks judge two holds' tiling by their drawn outlines too (the item of the hold's row on its box).
    Break: score/review/plan_checks.py: `boxes = [hold_outline(plan, hold) for hold in holds]` ->
        `boxes = [hold_outline({}, hold) for hold in holds]`
    A free redrawing under the owner's standing word on design fixes is kept as an edit with its reason, and shown with
    what it lays past its outline brought inside; one giving a field no drawing has, or no reason, is refused.
    Break: score/review/plans.py: `if shown is None or shown["how"] not in ("edited", "revised", "redrawn"):` ->
        `if shown is None or shown["how"] not in ("edited", "revised"):`
    Break: score/review/plans.py: `if unknown:` -> `if False:`
    Break: score/review/plans.py: edit_inside's `plan, moved = people_moved_out(plan, inventory or {"rows": []})` dropped
        (greenhouse's redrawn astronaut_2 kept in its grow light frame, 2026-11-08)
    Break: score/review/plans.py: edit_inside's `fixes += plan_fixes.kept_apart(plan, inventory or {"rows": []})`
        dropped (the bay's redrawn second stove kept 0.9 m up on its first)
    Break: score/review/plans.py: `if not (asked or {}).get("words") or not asked.get("at") or not asked.get("reason"):` ->
        `if False:`
    A hold fitted to its plan's size takes its row's drawn item with it and moves, its item too, so its door meets its
    sibling's, backed off along its door's wall, a sibling's own drawn item left (the base's airlock and tube#3).
    Break: score/review/plans.py: hold_fitted's `item_redrawn(plan, hold, old, new)` dropped
    Break: score/review/plans.py: mover_of's `or place in fitted` dropped
    Break: score/review/plans.py: doors_met's `box = backed_off(...) or pushed_out(box, sibling)` made
        `box = pushed_out(box, sibling)`
    Break: score/review/plans.py: doors_met's `or number in drawn` dropped
    A writing's doorway to a sibling held once whose own plan leads no doorway back leads nowhere, said in its fixes; one
    a sibling's door meets, or a lead of its own names, stays (the Square's street to the stairwell, 2026-11-06).
    Break: score/review/plans.py: doors_led's `opening["to"] = None` dropped
    Break: score/review/plans.py: doors_led's `or doors_to(as_held(once_held[sibling], found), place)` dropped
    Break: score/review/plans.py: doors_led's `{sibling, opening.get("to")} & named` made `set()`
    A doorway its own hold leads elsewhere is judged there (the base's airlock door to the hub, led to tube#3).
    Break: score/review/plans.py: doors_led's `led = as_held(once_held[place], plan).get("openings") or []` made
        `led = plan.get("openings") or []`
    A writing's doorway to a name that is no place of the design nor a row of its inventory leads nowhere, said; one to
    a row, a place or sealed stays (the Square's street's door to 'restaurant', 2026-11-07).
    Break: score/review/plans.py: doors_known's `opening["to"] = None` dropped
    Break: score/review/plans.py: doors_known's `or to in rows` dropped
"""
import contextlib
import copy
import datetime
import functools
import hashlib
import io
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import numpy
import pytest
from PIL import Image

from score import checks, contracts, graph, review, stages
from score.adapters import compute
from score.review import (concepts, creator_plans, discuss, environment_concept, environment_concept as ec, environment_plan,
                          holders, overhead, plan_checks, plan_drawing, plan_fixes, plan_writing, plans, plans_pass, reading,
                          reading_fixes, scene_sky, setting, standing, web)
from score.stages.scene_record import plan as record_plan
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


def square_home(home):
    """A home of the test's own holding the Square's places' kept plans (SQUARE_PLANS), never the real home's."""
    plans = home / "design" / "plans"
    plans.mkdir(parents=True)
    for place, plan in SQUARE_PLANS.items():
        (plans / f"{place}.json").write_text(json.dumps(plan))
    return home


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


def gapped_card(*findings):
    """A scorecard that fails only on its accepted gaps, with those findings ("<gap>: <fault>", the gap object-led)."""
    return {"likeness": {"answer": checks.PASS, "measures": {}},
            review.GAPPED: {"answer": checks.FAIL, "measures": {"gaps": len(findings)}, "findings": list(findings)}}


def card(answer, **measures):
    sides = {"halo": "higher", "veil": "lower", "faults": "lower", "lowest clap": "higher", "ferry reach": "lower",
             "stray": "lower"}
    return {"heads": {"answer": answer, "measures": measures, "better": {name: sides[name] for name in measures}}}


REGRESSIONS = [  # (row, new card, accepted card, worse: a bool, or the exact lines)
    ("halo 0.01 darker reads the same (the owner, 2026-10-13: a 2% step)", card("pass", halo=0.31),
     card("pass", halo=0.32), False),
    ("veil within its step", card("pass", veil=0.059), card("pass", veil=0.04), False),
    ("halo 0.02 is worse", card("pass", halo=0.30), card("pass", halo=0.32), True),
    ("one more fault", card("pass", faults=3), card("pass", faults=2), True),
    ("a score no viewer reads: any move", card("pass", **{"lowest clap": 0.3760}),
     card("pass", **{"lowest clap": 0.3761}), True),
    ("4 mm: unseen", card("pass", **{"ferry reach": 0.024}), card("pass", **{"ferry reach": 0.02}), False),
    ("6 mm: seen", card("pass", **{"ferry reach": 0.026}), card("pass", **{"ferry reach": 0.02}), True),
    ("under half a percent of a surface", card("pass", stray=0.0001), card("pass", stray=0.0), False),
    ("stray seen", card("pass", stray=0.006), card("pass", stray=0.0), True),
    ("an answer that drops is worse whatever its measures did", card("fail", halo=0.33), card("pass", halo=0.32),
     ["heads: pass became fail"]),
]

WRECK_OLD = ["/wreck/Objects/leg_strut_1: floats 0.0469: nothing under it",
             "/wreck/Objects/leg_foot_1: tips 0.2474: its weight falls outside", "/wreck/Objects/crate_1: sunk 0.03: below"]
WRECK_NEW = ["/wreck/Objects/leg_strut_1: tips 0.4439: its weight falls outside",
             "/wreck/Objects/forward_section_1: unstable 0.3228: moves", "/wreck/Objects/crate_1: sunk 0.03: below"]
GAPPED_WORSE = [  # (row, node, the new resting findings, the got-worse lines or None for any): a wreck gap, 3 objects
    ("the gap's objects at new faults pass", "assembly@wreck", WRECK_NEW, []),
    ("another object at a new fault still reads worse", "assembly@wreck",
     WRECK_NEW + ["/wreck/Objects/hull_plate_1: tips 0.3: outside"],
     ["resting: objects 2 became 3 (lower is better; worse from 1)"]),
    ("an existing fault outside the gaps grows", "assembly@wreck",
     [finding.replace("crate_1: sunk 0.03", "crate_1: sunk 0.09") for finding in WRECK_NEW], None),
    ("no gap reaches this node's gate", "assembly@hub", WRECK_NEW, None),
]


def test_the_owners_word_stands(tally, store, tmp_path, monkeypatch):
    """One store's tally node: the runner takes a passing output and nothing worse; a worse or failed one only the
    owner takes, by his own signed-in name, with his written reason or waiver; within his worse accept the runner
    follows him and no further; his reject sticks; his commands and his stop line refuse anyone else. Each judging
    case (a measure's step, an answer's drop, a gap's objects) is a row read through the same judge. What the review
    works out for him stands against answers known apart from the code: environment 1's setting from the cited table,
    a house's and an invented body's, each setting off its shape a refused row; and each sky (the Moon's phases, the Sun
    at Greenwich, a house's sun path) a row read through the same overhead. A reading's rows are what both readers
    agree on and an answer off its schema is refused, each a row through the same judge, as are a reading's fixes
    (parts, seats), a call's cost, sites cleared on a plot and a footprint measured from its boxes; a written plan's
    gaps against its concept, its reach, inside places and stairs are rows read through the same plan check, and the
    writer lays the stair core's flights with none; the plan writer's fixes (a thing the creator planned laid from his
    plan, a scene added in the app given its holder's doors into it, a missing thing piled only on its own row's pile,
    a box drawn apart split) are rows of what each answers and the plan it leaves. A picked place's reading in a store of its own: read once inside
    its clearance, an answer off its schema kept with its cost and asked again, its parts and its concept's light
    asked after it once each (again under a newer parts version or when named again), an older method's reading read
    again by SAM 3 only, a part merged into its thing free, and a new pick with no reading until read. The
    environment concept in a store of its own: today's data shown locked, an ask and a Send only inside his yes at today's price, a draw and pick out of date once he unlocks and
    refused until he locks again, a reference kept and a concept out of shape refused while unlocked, his locked
    version what every draw reads, and an agent's process keeping no version or reference. The concept draws in a store
    of their own: every generated wording from its place's data, short and in words; the campgrounds drawn, copied off
    this PC, edited, discussed and redrawn from his marks only inside his yes at today's measured price, picked only
    by him; and each layer drawn only once the one above is picked, read and planned, its crop and the places it opens
    into sent, a new pick above putting it out of date. The environment plan in a store of its own, one case table of
    his settings and the scenes' plans: each top scene
    where his setting puts it, shaped by its own plan, cleared of its neighbours along their bearings unless he
    placed it, at true distances; a written plan keeping those fixed facts, his edit settled again and its daylight
    sun brought up, out of date under a new concept, written only under the allowance; a house on a plot under its own
    sun, its rooms keeping its sky; a new environment's sites placed by physics and never compared across grounds. The
    plan review in a store of its own, a yard holding a shed: no plan before the inventory counts, then each item tied
    to its row; a holder with no outline of its own given one round its inside places; his edits kept as his own and
    checked, and sent with a Correct that has no note; a correction only inside his yes at today's price; the plan
    stage reading his plan and dropping it once the pick goes; a scene he added in the app, or a parent scene with no
    data of its own, a place once its design is done, the parent scene listed first; then, the yard read again round
    the shed, each spot taking its child scene's own plan size centred where it sat and saying so, turned with its
    hold, fitted to its shape, its doors met, led or leading nowhere, said. The plan writing in a store of its
    own: a writing only under the allowance or inside his yes at today's price, the shed's a plan of the stage tables'
    schema with each failed check a named gap, written once unless asked again; a reading writing its plan only under
    the allowance; a read place owed unless refused, and an older method's dearer call no price of today's."""
    def page():
        return review.page(tally.store, NODE).read_text()

    def accepted():
        return tally.store.accepted(NODE)

    first = tally(1)  # passes, nothing accepted yet: the runner takes it
    assert accepted() == first and tally.store.current_accept(NODE)["by"] == RUNNER
    assert "Unverified seed." in page() and "The runner accepted this output automatically" in page()

    second = tally(2)  # passes, but worse: the runner leaves it, and so do the owner's commands without his reason
    assert accepted() == first
    assert "faults 1 became 2" in refusal(lambda: review.accept(tally.store, NODE, second, "owner"))
    assert "worse than the accepted one" in refusal(lambda: web.decide(tally.store, NODE, second, "accept", by="joey"))
    assert accepted() == first
    assert "with the Accept button on the cockpit's page of tally@hangar, saying why it may be worse" in page()
    given = web.decide(tally.store, NODE, second, "accept", by="joey", worse_reason="two faults are fine")
    assert given["by"] == "joey" and given["worse_reason"] == "two faults are fine" and accepted() == second
    assert given["worse"] == ["faults: faults 1 became 2 (lower is better; worse from 1)"]
    assert given["allowed"] == {"faults": {"faults": {"from": 1, "to": 2}}}
    assert "The owner accepted it" in page()

    better = tally("1\n")  # better (a key of its own): the runner takes it as ever
    assert accepted() == better and tally.store.current_accept(NODE)["by"] == RUNNER
    fourth = tally("2\n")  # worse than the one before, as bad as the one he took: the runner follows his accept
    assert accepted() == fourth and tally.store.current_accept(NODE)["reason"].startswith(
        f"accepted automatically: within the owner's accept of {given['at'][:10]} ({second[:12]})")
    tally(3)  # beyond what he allowed: it waits for him
    assert accepted() == fourth

    assert "not tally@hangar's accepted output" in refusal(
        lambda: review.reject(tally.store, NODE, second, "owner", "w"))
    assert "needs a reason" in refusal(lambda: review.reject(tally.store, NODE, fourth, "owner", " "))
    review.reject(tally.store, NODE, fourth, "owner", "two faults here are real")
    assert accepted() == better  # moved back to the one accepted before it
    assert review.accept_automatically(tally.store, NODE, fourth) is None
    tally("2\n")  # the runner runs the same key again: it never takes the rejected output back
    assert accepted() == better and "The owner rejected this output." in page()
    review.accept(tally.store, NODE, fourth, "owner", "on a second look it is right", worse_reason="as he allowed")
    assert accepted() == fourth

    pulled = tally.store.records  # an accept pulled before its record: nothing known to be worse than, so it is taken
    tally.store.records = lambda node: [record for record in pulled(node) if record["output"] != fourth]
    pulled_worse = tally("3\n")  # worse than the accepted one and beyond his allowance, yet taken
    assert accepted() == pulled_worse and tally.store.current_accept(NODE)["by"] == RUNNER
    del tally.store.records

    failed = tally(9)  # fails its gate: offered to no one, refused from his command and the web alike
    assert accepted() == pulled_worse
    assert "It cannot be accepted" in page() and "Accept button" not in page()
    off_his_rules = [  # (output, decision, named, the refusal's words): a web decision off his rules
        (first, "accept", {"by": ""}, "signed-in owner's own name"),
        (first, "accept", {"by": "  "}, "signed-in owner's own name"),
        (first, "accept", {"by": None}, "signed-in owner's own name"),
        (first, "accept", {"by": "runner"}, "signed-in owner's own name"),
        (first, "waive", {"by": "joey"}, "one of accept, reject"),
        (failed, "accept", {"by": "joey"}, "answered fail"),
        (pulled_worse, "reject", {"by": "joey", "reason": " "}, "needs a reason"),
    ]
    for output, decision, named, why in off_his_rules:
        assert why in refusal(lambda: web.decide(tally.store, NODE, output, decision, **named)), (decision, named)
    assert "answered fail" in refusal(lambda: review.accept(tally.store, NODE, failed, "owner"))
    key = review.record_of(tally.store, NODE, failed)["key"]
    assert "needs a reason" in refusal(lambda: review.waive(tally.store, NODE, key, "faults", "owner", " "))
    assert "has no check" in refusal(lambda: review.waive(tally.store, NODE, key, "tilt", "owner", "why"))
    review.waive(tally.store, NODE, key, "faults", "owner", "the nine are one fault seen nine times")
    assert "Waived by owner" in page() and "the nine are one fault seen nine times" in page()
    review.accept(tally.store, NODE, failed, "owner", worse_reason="waived")
    assert accepted() == failed
    later = tally(10)  # a new key: the waiver does not carry over
    assert "answered fail" in refusal(lambda: review.accept(tally.store, NODE, later, "owner"))
    web.decide(tally.store, NODE, failed, "reject", by="joey", reason="looked again later")  # his web reject stands
    assert accepted() == pulled_worse

    for words in (["reject", NODE, failed, "--reason", "x"], ["accept", NODE, failed],
                  ["waive", NODE, "k", "faults", "--reason", "x"]):  # his commands, run without his terminal
        ran = subprocess.run([sys.executable, "-m", "score.review", *words], cwd=REPO, capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, env={**os.environ, "PROPS_HOME": str(tmp_path / "home")})
        assert ran.returncode != 0 and "only the owner" in ran.stderr, (words, ran.stderr)

    from score.adapters.compute import guard  # C22 from the cockpit: his checkout writes the world's stop line
    from score.store import AGENT_MARKERS
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    books = {"month": "2026-10", "bill": 50.0, "ledger": 40.0, "google": 0.0}
    assert "signed-in owner's own name" in refusal(
        lambda: web.stop(tally.store, "toy", 9.0, "films", by="runner", books=lambda: books))
    line = web.stop(tally.store, "toy", 9.0, "checkout 1: fix-sound", by="joey", books=lambda: books)
    assert line["by"] == "joey" and line["baseline"] == books and guard.current(tally.store, "toy")["euros"] == 9.0
    raised = web.stop(tally.store, "toy", 12.0, "checkout 2", by="joey", books=lambda: {})
    assert raised["before"] == 9.0 and raised["baseline"] == books  # a first line counts from the books given
    monkeypatch.setenv(AGENT_MARKERS[0], "1")
    with pytest.raises(PermissionError):
        web.stop(tally.store, "toy", 99.0, "an agent's", by="joey", books=lambda: books)
    assert guard.current(tally.store, "toy")["euros"] == 12.0

    for row, new, old, worse in REGRESSIONS:  # worse only by a step a viewer could see, or a dropped answer
        found = review.regressions(new, old)
        assert (found == worse) if isinstance(worse, list) else (bool(found) == worse), (row, found)

    # accepted gaps pass a place on with one gap object; shiplock's nine and cockpit's eleven (2026-11-12) stay failed
    one = gapped_card("hatch: no model: hatch: none", "hatch: thin: hatch: 2 mm")
    nine = gapped_card(*(f"part_{number}: no model: part_{number}: none" for number in range(9)))
    assert review.fails_only_on_gaps(one, set()) and review.gapped_status(one, set()) == \
        "complete apart from accepted gaps (2)"
    assert not review.fails_only_on_gaps(nine, set()) and review.gapped_status(nine, set()) is None

    # an accepted gap's objects leave the got-worse comparison (assembly@wreck, 2026-10-16); any other object blocks
    from score.stages import gaps

    def resting(objects, findings):
        return {"resting": {"answer": "pass", "measures": {"objects": objects}, "better": {"objects": "lower"},
                            "findings": findings}}
    monkeypatch.setattr(review, "accepted_card", lambda store, node, output: resting(2, WRECK_OLD))
    monkeypatch.setattr(gaps, "FOLDER", tmp_path / "checks/gaps")  # the owner's decision, written here
    gaps.FOLDER.mkdir(parents=True)
    (gaps.FOLDER / "wreck.json").write_text(json.dumps({"gaps": [{
        "name": "wreck: three pieces do not rest", "row": "assembly", "check": "resting",
        "objects": ["/wreck/Objects/leg_strut_1", "/wreck/Objects/leg_foot_1", "/wreck/Objects/forward_section_1"],
        "reason": "a test's decision", "decided": "owner, 2026-10-16", "faults": []}]}))
    for row, node, findings, lines in GAPPED_WORSE:
        got = review.worse_than_accepted(None, node, {"output": "new", "verdicts": resting(3, findings)})
        assert (got == lines) if lines is not None else got != [], (row, got)

    # the setting: real bodies from the cited table, each value naming its source; invented ones whole
    table = setting.reference()
    for key, body in table["bodies"].items():
        assert set(body["cited"]) == {field for field in body if field != "cited"}, key
        assert all(source in table["sources"] for source in body["cited"].values()), key
    environment_1 = setting.now()
    bodies = {body["body"]: body for body in environment_1["bodies"]}
    assert set(bodies) == {"sun", "earth", "moon", "mars"} and environment_1["plots"] == []
    assert {key: bodies[key]["gravity"] for key in ("earth", "moon", "mars")} == pytest.approx(
        {"earth": 9.82, "moon": 1.62, "mars": 3.73}, abs=0.005)  # NASA's fact sheets: surface gravity (mean)
    assert bodies["moon"]["radius_km"] == 1737.4 and bodies["moon"]["locked_to"] == "earth"
    assert bodies["moon"]["distance_km"] == pytest.approx(384400, rel=1e-3)
    assert {site["place"]: site["on"] for site in environment_1["sites"]} == {
        "square": "earth", "wreck": "moon", "old_station": "moon", "base": "moon", "campgrounds": "mars"}
    assert bodies["sun"]["kelvin"] == 5772.0 and bodies["sun"]["lux"] == 128000.0  # the body and the light it gives
    assert "lux" not in bodies["earth"] and environment_1["lights"] == []
    assert environment_1["backdrops"] == [{"backdrop": "stars", "name": "Stars", "shape": "dome", "lux": 0.0001}]
    house = setting.checked(HOUSE)  # a house on a plot needs no bodies: its sun is a light
    assert house["bodies"] == [] and house["plots"] == [{"plot": "meadow", "name": "Meadow", "gravity": 9.81}]
    assert house["lights"][0]["light"] == "sun" and house["lights"][0]["day_hours"] == 24.0
    assert house["backdrops"] == [{"backdrop": "sky", "name": "Sky", "shape": "dome", "lux": 10000.0}]
    assert house["sites"] == [{"place": "house", "on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}]
    earth = setting.checked({"bodies": [{"reference": "sun"}, {"reference": "earth", "day_hours": "30",
                                                                "radius_km": "7000,5"}]})["bodies"][1]
    assert earth["radius_km"] == 7000.5 and earth["day_hours"] == 30.0 and "pole_ra_deg" not in earth  # his own day
    assert earth["mass_kg"] == 5.9722e24 and earth["name"] == "Earth"  # the rest the table's
    for row, off_shape, words in REFUSED_SETTINGS:
        with pytest.raises(setting.Refused) as refused:
            setting.checked(off_shape)
            pytest.fail(f"{row}: taken")
        assert re.search(words, str(refused.value)), (row, str(refused.value))
    assert setting.proposed({"bodies": [{"body": "moon", "name": "Moon", "reference": "moon", "radius_km": 220}]})[
        "bodies"] == [{"body": "moon", "name": "Moon", "reference": "moon"}]  # a model's values give way to the table's
    rounded = [{**site, "latitude": 55.0, "longitude": 0.0} if site["on"] == "moon" else site
               for site in environment_1["sites"]]  # a model's answer stacking the Moon's sites on one spot
    assert setting.kept_apart({**environment_1, "sites": rounded}, environment_1)["sites"] == environment_1["sites"]
    spots = [setting.spot(site) for site in environment_1["sites"]]
    assert len(set(spots)) == len(spots)  # environment 1's proposal: each site its own spot
    moved = [{**site, "longitude": 0.5} if site["place"] == "base" else site for site in environment_1["sites"]]
    assert setting.kept_apart({**environment_1, "sites": moved}, environment_1)["sites"] == moved  # one he moves moves

    # overhead: each sky read against one known apart from the code
    for row, seen_from, when, key, field, expected in SKIES:
        got = thing_in(sky(environment_1["bodies"], seen_from, when), key)[field]
        assert above(got, *expected) if isinstance(expected, tuple) else got == expected, (row, got)
    from_moon = [thing_in(sky(environment_1["bodies"], ("moon", 55.0, 0.0), f"2099-06-{day:02d}T12:00:00Z"), "earth")
                 ["altitude"] for day in (1, 8, 15)]
    assert max(from_moon) - min(from_moon) < 1  # Earth over a near-side Moon site is locked: it stays
    house_noon = sky(None, "house", "2024-03-20T12:00:00Z")  # a house's sky holds no bodies, under its own backdrop
    assert house_noon["bodies"] == [] and house_noon["backdrops"][0]["name"] == "Sky"
    base = next(site for site in environment_1["sites"] if site["place"] == "base")
    over_base = overhead.seen(environment_1, base, "2099-06-01T12:00:00Z")
    assert [light["of"] for light in over_base["lights"]] == ["sun"]
    assert {body["body"] for body in over_base["bodies"]} == {"earth", "mars"}  # never the Moon it stands on, nor Sun
    assert over_base["backdrops"] == [{"name": "Stars", "shape": "dome", "lux": 0.0001}]
    home = {"body": "home", "name": "Home", "radius_km": 5000.0, "mass_kg": 5e24, "around": "star",
            "distance_km": 1.2e8, "period_days": 300.0, "eccentricity": 0.0, "inclination_deg": 0.0,
            "day_hours": 30.0, "tilt_deg": 0.0}  # an invented body turning by its own day under an invented star
    invented = [{"body": "star", "name": "Star", "radius_km": 600000.0, "mass_kg": 2e30, "kelvin": 4000.0,
                 "lux": 1e5, "lux_at_km": 1.2e8}, home]
    start = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
    heights = [thing_in(sky(invented, ("home", 0.0, 0.0), (start + datetime.timedelta(hours=hour)).isoformat()),
                        "light")["altitude"] for hour in range(31)]
    assert max(heights) > 80 and min(heights) < -80  # on its equator the star passes over and under once a day
    again = thing_in(sky(invented, ("home", 0.0, 0.0), "2100-01-02T06:00:00Z"), "light")["altitude"]
    assert again == pytest.approx(heights[0], abs=1.5)  # back where it was, less its orbit's turn of 1.5 degrees

    # the scene inventory reading: only what both readers agree on is a row, each answer off its schema refused
    for row_name, rows, found_by_sam, size, kept, skipped, merged in AGREED:
        got = reading.agreed(rows, [], found_by_sam, size)
        for want, answer in zip((kept, skipped), got):
            assert want is None or holds(answer, want), (row_name, answer)
        assert merged is None or got[2] == merged, (row_name, got[2])  # the merged column exactly, no extra key
    assert reading.inside_rows(INSIDE_ROWS, {"hangar"}) == {"hangar", "ship", "hatch"}  # an inside place's own, kept
    for row_name, function, arguments, want in [*READ_ANSWERS, *SEATED_AND_PARTED, *PRICED_AND_CLEARED, *MEASURED]:
        function = getattr(reading, function) if isinstance(function, str) else function
        if isinstance(want, Refusal):
            with pytest.raises(concepts.Refused, match=want):
                function(*arguments)
                pytest.fail(f"{row_name}: taken")
        else:
            answer = function(*arguments)
            assert holds(answer, want), (row_name, answer)
    seated = reading_fixes.seats_added(ALONE)[0]  # the bench added: its sitter seated, no part merged
    assert reading_fixes.seats_missing(seated) == {} and reading_fixes.parts_apart(seated, SIZE)[1] == []
    parts = reading.parts_schema(["drum", "mast"])["properties"]["parts"]  # the parts ask answers under a schema
    assert parts["required"] == ["drum", "mast"] and parts["properties"]["mast"]["enum"] == list(reading.PARTS)

    # a written plan's gaps against its concept: where each row stands and faces, what joins, what counts
    for row_name, plan, inventory, kinds, want in GAP_WORDS:
        words = [gap["words"] for gap in plan_checks.checked(plan, inventory) if kinds is None or gap["kind"] in kinds]
        assert (want <= set(words)) if isinstance(want, set) else words == want, (row_name, words)
    stairs, levels = plan_writing.flights_laid(STAIR_CORE)  # the writer lays the core's flights with no stair gap
    assert not plan_checks.stair_gaps({**STAIR_CORE, "stairs": stairs, "levels": levels})
    assert all(0.15 <= (stair["to"] - stair["from"]) / stair["steps"] <= 0.19 and 0.25 <= plan_checks.flight(
        stair)[3] / stair["steps"] <= 0.30 for stair in stairs), stairs
    assert [level["name"] for level in levels] == ["landing at 1.5 m", "landing at 3 m"], levels
    # the plan writer's free fixes, each on a plan of its own: what it answers and the plan it leaves
    with monkeypatch.context() as his_ship:
        his_ship.setattr(creator_plans, "PLANS", (lambda: SHIP,))
        his_ship.setattr(plan_fixes, "corrected", correcting)
        for row_name, fix, arguments, want, plan_want, *again in FIXED:
            arguments = copy.deepcopy(arguments)
            answer = fix(*arguments)
            assert answer is arguments[0] if want is THE_PLAN_ITSELF else holds(answer, want), (row_name, answer)
            assert not again or holds(fix(*arguments), again[0]), (row_name, "given its own plan again")
            assert plan_want is None or holds(arguments[0], plan_want), (row_name, arguments[0])

    monkeypatch.delenv(AGENT_MARKERS[0])
    # a picked place's reading in a store of its own: read once inside its clearance, an answer off its schema kept
    # with its cost and read again, its parts and its concept's light asked after it once each, an older reading read
    # again by SAM 3 only, a part fixed free, a new pick with no reading until read
    read_store = Store.in_folder(tmp_path / "reading")
    sha = picked_place(read_store, tmp_path)
    cleared = []

    def clear(store, places, euros):
        cleared.append((places, euros))
        return compute.reading_clearance(store, places, euros)
    with pytest.raises(concepts.Refused, match="lab: no locked concept"):  # read only after its own pick
        reading.read(read_store, ["wreck", "lab"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
    off = lambda store, place, folder: ("row 'earth' has no valid anchor", 0.02, 9.0, None, None)  # noqa: E731
    assert reading.read(read_store, ["wreck"], "joey", ask=off, boxes=stand_in_boxes) == []
    [refused] = reading.readings(read_store, "wreck")
    assert "anchor" in refused["refused"] and reading.spent(read_store, ["wreck"]) == 0.02  # its cost kept
    assert reading.reading_of(read_store, "wreck") is None and reading.to_read(read_store, ["wreck"]) == ["wreck"]
    with monkeypatch.context() as patched:
        patched.setattr(compute, "READING_GEMINI_EUROS", 0.05)
        assert cleared == []
        [record] = reading.read(read_store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
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
    assert reading.reading_of(read_store, "wreck") == record
    assert reading.spent(read_store, ["wreck", "lab"]) == round(0.02 + 0.15, 4)
    assert reading.read(read_store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes) == []
    assert len(cleared) == 1  # read from this pick already: nothing asked, nothing cleared
    assert reading.row_boxes(read_store, "wreck", "drum_right") == [[150, 10, 170, 30]]
    assert reading.row_boxes(read_store, "wreck", "lamp") is None
    assert reading.row_boxes(read_store, "wreck", "nothing") is None
    assert reading.row_boxes(read_store, "lab", "drum") is None

    ids = [row["id"] for row in record["inventory"]["rows"]]  # its parts: asked once, inside the reading's clearance
    assert reading.unparted(read_store, ["wreck"]) == ["wreck"]  # the stand-in answered no parts
    for answer in ('{"parts": {"drum": "object", "drum_right": "object"}}',
                   '{"parts": {"drum": "object", "drum_right": "object", "mast": "pole"}}'):
        with pytest.raises(concepts.Refused, match="'mast'"):  # a row missing, or a part off PARTS
            reading.parts_of(answer, ids)
    off = lambda store, place, folder: ("no valid part for 'mast'", 0.01, 3.0)  # noqa: E731
    assert reading.parted(read_store, ["wreck"], "joey", ask=off) == []
    assert reading.unparted(read_store, ["wreck"]) == ["wreck"]  # refused: asked again next time
    parts = lambda part: lambda store, place, folder: (reading.parts_of(  # noqa: E731
        '{"parts": {"drum": "object", "drum_right": "object", "mast": "%s"}}' % part, ids), 0.02, 4.0)
    [kept] = reading.parted(read_store, ["wreck", "lab"], "joey", ask=parts("structure"))
    assert kept["reading"] == record["at"] and kept["parts"]["mast"] == "structure"
    now = reading.reading_of(read_store, "wreck")
    assert [row["part"] for row in now["inventory"]["rows"]] == ["object", "object", "structure"]
    assert now["at"] == record["at"] and reading.unparted(read_store, ["wreck"]) == []  # its rows kept
    assert reading.parted(read_store, ["wreck"], "joey", ask=None) == []  # parted already: nothing asked
    assert reading.spent(read_store, ["wreck"]) == round(0.02 + 0.15 + 0.01 + 0.02, 4)

    dark = {"glows": False, "glowing": "", "colour": "", "brightness": 0}  # its concept's light: asked once
    lamp = {"id": "mast", "glows": True, "glowing": "its lamp", "colour": "#ffd29a", "brightness": 0.5}
    scene = {"daylight": False, "unseen": True, "unseen_colour": "#8899aa"}
    lit_answer = lambda rows, seen=scene: json.dumps({"rows": rows, "scene": seen})  # noqa: E731
    lit_rows = [{"id": "drum", **dark}, {"id": "drum_right", **dark}, lamp]
    for answer, why in ((lit_answer(lit_rows[:2]), "every row"),
                        (lit_answer(lit_rows[:2] + [{**lamp, "colour": "warm"}]), "'mast'"),
                        (lit_answer(lit_rows, {**scene, "unseen_colour": ""}), "'scene'")):
        with pytest.raises(concepts.Refused, match=why):
            reading.light_of(answer, ids)
    assert reading.light_schema(ids)["properties"]["rows"]["items"]["properties"]["id"]["enum"] == ids
    assert reading.unlit(read_store, ["wreck"]) == ["wreck"]
    lights = lambda text: lambda store, place, folder: (reading.light_of(text, ids), 0.03, 5.0)  # noqa: E731
    unseen_off = {"daylight": False, "unseen": False, "unseen_colour": ""}
    [kept] = reading.lit(read_store, ["wreck", "lab"], "joey", ask=lights(lit_answer(
        [{"id": item, **dark} for item in ids], unseen_off)))
    assert kept["reading"] == record["at"] and not reading.concept_light(read_store, "wreck")["scene"]["unseen"]
    assert reading.unlit(read_store, ["wreck"]) == [] and reading.lit(read_store, ["wreck"], "joey", ask=None) == []
    [again] = reading.lit(read_store, ["wreck", "lab"], "joey", ask=lights(lit_answer(lit_rows)), again=True)
    assert again["reading"] == record["at"]  # named again (its words changed): asked once more, the newest read
    assert reading.concept_light(read_store, "wreck")["scene"]["unseen"]
    assert reading.concept_light(read_store, "wreck")["rows"]["mast"]["glows"]
    assert reading.spent(read_store, ["wreck"]) == round(0.02 + 0.15 + 0.01 + 0.02 + 0.03 + 0.03, 4)
    from score.graph import _code  # the light's words are a file the ask reads, in no paid row's code
    glows_line = (concepts.DATA / "reading/light.txt").read_text().splitlines()[2]  # its own words, no other ask's
    held = _code.source_files([reading.asked_light, reading.lit])
    assert _code.REPO / "score/review/reading.py" in held and not any(glows_line in path.read_text() for path in held)
    with monkeypatch.context() as patched:
        words, bodies = tmp_path / "light.txt", []
        words.write_text("Say how the place is lit, a lamp out of view at night too.\n{rows}")
        patched.setattr(reading, "LIGHT_ASKED", words)
        patched.setattr(reading, "asked", lambda body: (bodies.append(body), ({}, 1.0))[1])
        patched.setattr(reading, "answer_text", lambda response: "{}")
        patched.setattr(reading, "call_euros", lambda response: 0.03)
        reading.asked_light(read_store, "wreck", tmp_path)
    assert bodies[0]["contents"][0]["parts"][0]["text"].startswith("Say how the place is lit, a lamp out of view")

    [again] = reading.read(read_store, ["wreck"], "joey", clear=clear, ask=None, boxes=stand_in_boxes, again=True)
    assert again["euros"]["rows"] == 0.0 and again["answered"] == record["answered"]  # its own rows, SAM 3 only
    assert reading.reading_of(read_store, "wreck") == again
    concepts.pick(read_store, "wreck", None, "joey")  # a new pick: no reading until it is read
    assert reading.reading_of(read_store, "wreck") is None and reading.to_read(read_store, ["wreck"]) == []

    with monkeypatch.context() as patched:  # rows answered under an older PARTS have their parts asked again once
        picked_place(read_store, tmp_path, "dock")
        patched.setattr(reading, "PARTS_VERSION", 1)
        reading.read(read_store, ["dock"], "joey", ask=parted_rows, boxes=stand_in_boxes)
        patched.setattr(reading, "PARTS_VERSION", 2)
        assert reading.unparted(read_store, ["dock"]) == ["dock"]
        [kept] = reading.parted(read_store, ["dock"], "joey", ask=parts("wall"))
        assert kept["version"] == 2 and reading.unparted(read_store, ["dock"]) == []
        rows = reading.reading_of(read_store, "dock")["inventory"]["rows"]
        assert [row["part"] for row in rows] == ["object", "object", "wall"]  # today's parts over its own
        assert reading.parted(read_store, ["dock"], "joey", ask=None) == []  # asked under today's version: not again

    hull = picked_place(read_store, tmp_path, "hull")  # a reading by an older method: read again by SAM 3 only
    old = [{**dict(READ_ROWS[2]), "view": "v1", "box": None, "boxes": [], "size": [0.4, 0.4, 18.0],
            "size_words": "tall", "thing": "", "name": "glass greenhouse dome", "noun": "building", "id": "greenhouse",
            "terrain": False, "kind": "generate", "anchor": "ground", "where": "left", "region": [0, 0, 1000, 1000]}]
    reading.kept(read_store, {"place": "hull", "concept": hull, "at": "2026-01-01T08:00:00+00:00", "by": "joey",
                              "method": 4, "size": [200, 100], "inventory": {"rows": old}, "gaps": [],
                              "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13}, "seconds": {}})
    asked = []

    def boxes(jobs, folder):
        asked.append([item["nouns"] for item in jobs[0]["rows"]])
        return {"hull.#greenhouse": [{"box": [10, 10, 90, 90]}], "hull.=building": []}, {
            "euros": 0.08, "wall_minutes": 5.0, "machines": []}
    never = lambda store, place, folder: pytest.fail("Gemini asked again")  # noqa: E731
    [record] = reading.read(read_store, ["hull"], "joey", ask=never, boxes=boxes)
    assert asked[0][:2] == [["glass greenhouse dome"], ["building"]]  # its own words, then its noun
    assert record["inventory"]["rows"][0]["boxes"] == [[10, 10, 90, 90]]
    assert record["from"].startswith("inventory-readings/hull/")
    assert record["euros"] == {"rows": 0.0, "boxes": 0.08, "total": 0.08}
    assert record["answered"][0]["metres"] == [0.4, 0.4, 18.0]
    assert reading.spent(read_store, ["hull"]) == 0.21 and reading.cost(read_store, record)["euros"] == 0.21

    shack = picked_place(read_store, tmp_path, "shack")  # a reading holding a part: fixed once, free
    reading.kept(read_store, {"place": "shack", "concept": shack, "at": "2026-01-01T08:00:00+00:00", "by": "joey",
                              "method": reading.METHOD, "parts_version": reading.PARTS_VERSION, "size": list(SIZE),
                              "inventory": {"rows": [FRIDGE, DOOR, HANDLE, CREW]}, "gaps": [], "skipped": [],
                              "merged": [], "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13}, "seconds": {}})
    assert reading_fixes.to_fix(read_store, ["shack"]) == ["shack"]
    [record] = reading_fixes.fix(read_store, ["shack"], "test")
    assert reading.reading_of(read_store, "shack") == record
    assert record["from"].startswith("inventory-readings/shack/")
    assert [(item["id"], item["anchor"]) for item in record["inventory"]["rows"]] == [
        ("fridge", "floor"), ("handle", "on:fridge"), ("crew", "on:crew_bench"), ("crew_bench", "floor")]
    assert record["seated"] == [{"row": "crew", "anchor": "on:crew_bench"}]
    assert record["merged"] == [{"name": "door", "row": "door", "into": "fridge"}]
    assert record["euros"]["total"] == 0.0 and record["parts_version"] == reading.PARTS_VERSION
    assert reading_fixes.to_fix(read_store, ["shack"]) == []
    assert reading_fixes.fix(read_store, ["shack"], "test") == []
    assert reading_fixes.said([record]) == "readings fixed: shack"
    assert reading_fixes.said([]) == "readings: none to fix"

    # concept draws, Discusses and picks in a store of their own: a paid call only inside his yes at today's price,
    # each wording from the place's data, a change above putting the draw under it out of date
    draws_store = Store.in_folder(tmp_path / "draws")
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    holder_words = concepts.holder_words  # the real holding row's name, before the layer above is stood in
    with monkeypatch.context() as patched:
        draws_home = square_home(tmp_path / "draws-home")  # the Square's kept plans and the hangar's reference
        patched.setattr(concepts, "PROPS_HOME", draws_home)  # the owner's private pictures: stand-ins, never his own
        for ref in concepts.references_of(draws_store, "hangar"):
            concepts.resolved(ref["picture"]).parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (8, 8)).save(concepts.resolved(ref["picture"]))

        # every generated wording, before anything is picked: from the place's data, short, in words not metres
        found = concepts.tree()
        for place in [*found["within"], *found["shells"], "square", "campgrounds", "old_station", "wreck"]:
            wording = concepts.generated(draws_store, place)
            assert len(wording) <= concepts.LONGEST_GENERATED, place
            for name in filter(None, [place, *concepts.inside_of(place), concepts.above(place)]):
                said = [concepts.inputs_of(name).get("says", ""), *concepts.inputs_of(name).get("holds", {}).values()]
                for words in said:  # owner (2026-10-20): only the creator's own says carry metres
                    wording = wording.replace(words.rstrip("."), "")
            assert not re.search(r"\d+(\.\d+)? ?m\b", wording), (place, wording)
        for place, view in (("base", concepts.OUTSIDE_VIEW), ("campgrounds", concepts.OUTSIDE_VIEW),
                            ("street", concepts.OUTSIDE_VIEW), ("cockpit", concepts.INSIDE_VIEW),
                            ("hangar", concepts.INSIDE_VIEW)):  # drawn from above outside, as a cutaway inside
            assert view in concepts.generated(draws_store, place), place
        street = concepts.generated(draws_store, "street")  # its design: people
        assert f"{concepts.EVERY_DRAW}, {concepts.WITH_PEOPLE}." in street
        hub = concepts.generated(draws_store, "hub")  # its design shows none and its look names none
        assert f"{concepts.EVERY_DRAW}, {concepts.NO_PEOPLE}." in hub and concepts.WITH_PEOPLE not in hub
        # owner, 2026-10-21: doors drawn lettered with room names; where a door leads is never written on it
        flat = concepts.generated(draws_store, "flat")
        assert ("Its unlabelled doors: balcony door (glass) onto the outside, over the square and the harbour; front "
                "door to the stair landing into the stairwell; no other doors or openings.") in flat
        assert "no text or signs" in flat
        assert "neighbour's door behind its gate (1st floor) (shut)" in concepts.generated(draws_store, "stairwell")
        rooms = {room: concepts.generated(draws_store, room) for room in SHIP_ROOMS}  # no two ship rooms alike
        assert len(set(rooms.values())) == len(SHIP_ROOMS)
        assert "for food: eat and prepare meals (counter, food stores, a table with fold-down seats)" in rooms["galley"]
        assert "pilot seats" in rooms["cockpit"] and "pilot seats" not in rooms["galley"]  # no copied look
        assert "on the port side" in rooms["quarters"] and "four bunks in two stacks" in rooms["quarters"]
        assert ("In the ship; for flying and navigating the ship, one room: the cockpit at the nose"
                in rooms["cockpit"])
        assert concepts.waits(draws_store, "launch") == "is part of the square's concept, with none of its own"
        assert "launch" not in [*concepts.undrawn(draws_store, ["square", "launch"])[0],
                                *concepts.undrawn(draws_store, ["square", "launch"])[1]]
        assert ("part of it: across the water in the distance, the rocket launch"
                in concepts.generated(draws_store, "square"))
        assert "It holds the ship, a crew shuttle 46 m long" in concepts.generated(draws_store, "hangar")
        assert concepts.sent_pictures(draws_store, "hangar")[-1][1].name == "shuttle-screenshot.png"
        assert "ship" not in found["within"] and "ship" not in found["shells"]  # no layer of its own
        assert concepts.above("cockpit") == "hangar"
        with monkeypatch.context() as barge:
            given = {"hangar": {"says": "It holds a barge 80 m long.", "references": []}, "hub": {"people": True}}
            barge.setattr(concepts, "inputs_of", lambda place: given.get(place, {}))
            hangar = concepts.generated(draws_store, "hangar")
            assert "It holds a barge 80 m long." in hangar and "46 m" not in hangar
            assert concepts.sent_pictures(draws_store, "hangar") == []  # no crop while the base is not ready
            assert concepts.WITH_PEOPLE in concepts.generated(draws_store, "hub")  # his say goes over the design
        with monkeypatch.context() as sized:  # ranked by the floor of each kept plan beside it, walls against a person
            sized.setattr(concepts, "PROPS_HOME", tmp_path / "sized-home")
            sizes = {"hangar": (15.0, 14.0, "walls 12 m"), "hub": (5.0, 6.0, ""), "lab": (4.0, 3.0, ""),
                     "tube": (3.0, 2.0, "")}
            (tmp_path / "sized-home/design/plans").mkdir(parents=True)
            for place in concepts.inside_of("base", draws_store):
                wide, deep, height = sizes.get(place, (4.0, 4.0, ""))
                (tmp_path / "sized-home/design/plans" / f"{place}.json").write_text(json.dumps(
                    {"w": wide, "d": deep, "height": height}))
            hangar = concepts.generated(draws_store, "hangar")
            assert ("Size: the largest in the base, floor about seven times any other's, walls towering over "
                    "people.") in hangar
            assert concepts.ROOF_KEPT in hangar and concepts.ROOF_KEPT not in concepts.generated(draws_store, "base")
            assert "Size: one of the smaller in the base" in concepts.generated(draws_store, "lab")
        # the campgrounds: drawn, copied off this PC, edited, discussed, redrawn from his marks, clicked and picked
        generated = concepts.generated(draws_store, "campgrounds")
        with pytest.raises(compute.Refused):  # no yes: no draw
            concepts.draw(draws_store, "campgrounds", {}, "joey", caller=stand_in([]))
        assert concepts.draws(draws_store, "campgrounds") == []
        key = said_yes(draws_store, patched)
        asked = []
        first = concepts.draw(draws_store, "campgrounds", {"note": "more dust"}, "joey", caller=stand_in(asked))
        assert first["yes"] == key and first["euros"] == 0.15 and first["base"] is None
        assert draws_store.objects.exists(f"blobs/{first['sha']}") and concepts.placed(draws_store) == ["campgrounds"]
        assert asked[-1] == (f"{generated} The creator's note: more dust", [])  # a top place: its wording alone
        assert concepts.own_wording(draws_store, "campgrounds") is None
        assert first["offsite"] == f"concept-draws/{first['sha']}.png"  # copied off this PC by its sha
        assert bucket.read_bytes(first["offsite"]) == draws_store.objects.read_bytes(f"blobs/{first['sha']}")
        assert json.loads(bucket.read_bytes(f"concept-draws/{first['sha']}.json"))["wording"] == first["wording"]

        class Down:
            def exists(self, key):
                raise ConnectionError("the bucket did not answer")
        said_yes(draws_store, patched)
        failed = concepts.draw(draws_store, "campgrounds", {}, "joey", caller=stand_in(asked), offsite=Down())
        assert failed["offsite"] is None and "did not answer" in failed["offsite_refused"]  # the draw kept, says why
        assert concepts.draws(draws_store, "campgrounds") == [first, failed] and asked[-1][0] == generated
        said_yes(draws_store, patched)
        edited = "One concept painting of the camp grounds, dusty."  # his edited wording, sent word for word
        concepts.draw(draws_store, "campgrounds", {"wording": f"  {edited}\n"}, "joey", caller=stand_in(asked))
        assert asked[-1][0] == edited and concepts.own_wording(draws_store, "campgrounds") == edited
        assert concepts.current_draw(draws_store, "campgrounds", concepts.wording_now(draws_store, "campgrounds"))
        assert not concepts.current_draw(draws_store, "campgrounds", "One concept painting of the camp grounds, clean.")

        patched.delenv("SCORE_SPEND_TICKET")  # a Discuss: inside his yes, its question, answer and cost kept
        marks = [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3, "note": "a red door"}]
        request = {"base": first["sha"], "question": "is the door too small?", "marks": marks}
        with pytest.raises(compute.Refused):
            discuss.discuss(draws_store, "campgrounds", request, "joey", asker=answerer([]))
        key = said_yes(draws_store, patched)
        asked_about = []
        entry = discuss.discuss(draws_store, "campgrounds", request, "joey", asker=answerer(asked_about))
        question, sizes = asked_about[0]  # the redraw's pictures (boxed, clean), its prompt, the mark's note
        assert "Box 1 (middle left): a red door." in question and "is the door too small?" in question
        assert first["wording"] in question and sizes == [(64, 40), (64, 40)]
        assert entry["answer"] == "Make the door red and wider." and entry["euros"] == 0.0271 and entry["yes"] == key
        assert discuss.discussions(draws_store, "campgrounds") == [entry]
        assert discuss.spent(draws_store, ["campgrounds"]) == 0.0271
        said_yes(draws_store, patched)
        asked_about = []
        discuss.discuss(draws_store, "campgrounds", {"base": first["sha"], "question": "warmer light?"}, "joey",
                        asker=answerer(asked_about, "Yes: late afternoon sun from the left."))
        thread = ("Creator: is the door too small?\nYou: Make the door red and wider.\nCreator: warmer light?\n"
                  "You: Yes: late afternoon sun from the left.")
        assert "Creator: is the door too small?\nYou: Make the door red and wider." in asked_about[0][0]
        with pytest.raises(concepts.Refused, match="a question"):
            discuss.discuss(draws_store, "campgrounds", {"base": first["sha"], "question": " "}, "joey",
                            asker=answerer([]))
        assert len(discuss.open_thread(draws_store, "campgrounds", first["sha"])) == 2

        said_yes(draws_store, patched)  # a redraw: the base boxed and clean, each mark's note, the thread
        asked, prompted = [], []
        second = concepts.draw(draws_store, "campgrounds", {"marks": marks, "note": "warmer", "base": first["sha"],
                                                            "wording": "ignored"},
                               "joey", caller=stand_in(asked), reviser=prompt_stand_in(prompted))
        question, seen = prompted[0]  # Gemini: the boxed and clean picture, the prompt it was drawn from, each note
        assert "Box 1 (middle left): a red door." in question and "Overall: warmer" in question and thread in question
        assert first["wording"] in question and seen == [(64, 40), (64, 40)]
        wording, sizes = asked[0]  # the draw: the corrected prompt, the box's note, the boxed and the clean picture
        assert wording.startswith("The corrected prompt.") and "Box 1 (middle left): a red door." in wording
        assert sizes == [(64, 40), (64, 40)] and "Overall: warmer" in wording and "Image 1" in wording
        assert second["base"] == first["sha"] and second["marks"][0]["note"] == "a red door"
        assert [call["model"] for call in second["calls"]] == [concepts.PROMPT_MODEL, "gemini-3-pro-image"]
        assert second["corrected"] == "The corrected prompt." == concepts.own_wording(draws_store, "campgrounds")
        assert concepts.current_draw(draws_store, "campgrounds", concepts.wording_now(draws_store, "campgrounds"))
        assert second["discussed"] == [talk["at"] for talk in discuss.discussions(draws_store, "campgrounds")]
        assert discuss.open_thread(draws_store, "campgrounds", first["sha"]) == []  # closed, kept for the record
        assert len(discuss.discussions(draws_store, "campgrounds")) == 2
        with pytest.raises(concepts.Refused, match="outside the picture"):
            concepts.draw(draws_store, "campgrounds", {"marks": [{"x": 0.9, "y": 0, "w": 0.5, "h": 0.1}],
                                                       "base": first["sha"]},
                          "joey", caller=stand_in([]), reviser=prompt_stand_in([]))
        with pytest.raises(concepts.Refused, match="no draw of"):
            concepts.draw(draws_store, "hub", {"base": first["sha"]}, "joey", caller=stand_in([]),
                          reviser=prompt_stand_in([]))
        said_yes(draws_store, patched)
        concepts.draw(draws_store, "campgrounds", {}, "joey", caller=stand_in(asked))  # Draw all's: no wording
        assert asked[-1][0] == "The corrected prompt."
        with pytest.raises(review.Refused, match="no wording of its own"):
            web.concept_generated(draws_store, "galley", "joey")
        web.concept_generated(draws_store, "campgrounds", "joey")  # back to generated
        assert concepts.wording_now(draws_store, "campgrounds") == generated
        with pytest.raises(concepts.Refused, match="at most"):
            concepts.draw(draws_store, "campgrounds", {"wording": "x" * 9000}, "joey", caller=stand_in(asked))

        older = [{"base": None, "wording": "an older wording"}]  # Draw all counts only a draw of today's wording
        with monkeypatch.context() as kept_draws:
            kept_draws.setattr(concepts, "draws", lambda _store, _place: older)
            assert concepts.undrawn(draws_store, ["old_station"])[0] == ["old_station"]
            older.append({"base": None, "wording": concepts.generated(draws_store, "old_station")})
            assert concepts.undrawn(draws_store, ["old_station"])[0] == []
            concepts.worded(draws_store, "old_station", "One concept painting of the old station at night.", "joey")
            assert concepts.undrawn(draws_store, ["old_station"])[0] == ["old_station"]  # its draw: the generated
            concepts.worded(draws_store, "old_station", None, "joey")
            assert concepts.undrawn(draws_store, ["old_station"])[0] == []
        per_unit = tmp_path / "per-unit.json"  # the prices: the measured calls at the standard tier
        measured = {"high_euros": 0.07048, "basis": "batch price of measured calls"}
        for kept_stages, priced, euros in (
                ({"closeup": measured}, concepts.draw_euros, 0.15),  # 0.07048 / 0.5 = 0.14096, up to the cent
                ({"closeup": measured, "finish-route-list": {"high_euros": 0.01665,
                                                             "basis": "batch price of measured calls"}},
                 concepts.redraw_euros, 0.18),  # (0.07048 + 0.01665) / 0.5 = 0.17426, up to the cent
                ({}, concepts.draw_euros, None)):
            per_unit.write_text(json.dumps({"stages": kept_stages}))
            assert priced(per_unit) == euros, (kept_stages, euros)
        patched.setattr(concepts, "draw_euros", lambda: 0.15)  # his click writes its yes at the price shown
        patched.setattr(concepts, "redraw_euros", lambda: 0.19)
        patched.setattr(discuss, "price", lambda: 0.04)

        def run(argv, env, **kwargs):  # the draw's or Discuss's own process, here in-process with a stand-in model
            patched.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
            asked_for = json.loads(open(argv[-2]).read())
            made = (discuss.discuss(draws_store, argv[-3], asked_for, argv[-1], asker=answerer([]))
                    if "question" in asked_for else
                    concepts.draw(draws_store, argv[-3], asked_for, argv[-1], caller=stand_in([])))
            return subprocess.CompletedProcess(argv, 0, json.dumps(made) + "\n", "")
        clicked = web.concept_draw(draws_store, "campgrounds", {"note": ""}, 0.15, "joey", run=run)
        talked = web.concept_discuss(draws_store, "campgrounds", {"base": first["sha"], "question": "why?"}, 0.04,
                                     "joey", run=run)
        for made, euros, purpose in ((clicked, 0.15, "campgrounds"), (talked, 0.04, "Discuss")):
            yes = draws_store.spend_yes("override", made["yes"])
            assert yes["by"] == "joey" and yes["euros"] == euros and purpose in yes["purpose"], purpose
        redraw = {"marks": [], "note": "warmer", "base": clicked["sha"]}
        for row, click in (
                ("a draw at another price",
                 lambda: web.concept_draw(draws_store, "campgrounds", {}, 0.10, "joey", run=run)),
                ("the runner's click", lambda: web.concept_draw(draws_store, "campgrounds", {}, 0.15, "runner",
                                                                run=run)),
                ("a redraw at a draw's price (two calls: its own price)",
                 lambda: web.concept_draw(draws_store, "campgrounds", redraw, 0.15, "joey", run=run)),
                ("a Discuss at another price",
                 lambda: web.concept_discuss(draws_store, "campgrounds", {"base": first["sha"], "question": "why?"},
                                             0.03, "joey", run=run))):
            with pytest.raises(review.Refused, match=None if "runner" in row else "not today's measured price"):
                click()
                pytest.fail(f"taken: {row}")

        with pytest.raises(concepts.Refused):  # his pick: only a draw of the place, and his unlock
            concepts.pick(draws_store, "campgrounds", "0" * 64, "joey")
        with monkeypatch.context() as agent:  # an agent's process picks nothing and keeps no wording
            agent.setattr(draws_store, "is_framework_store", lambda: True)
            agent.setattr(concepts, "running_under_agent", lambda: True)
            with pytest.raises(PermissionError):
                concepts.pick(draws_store, "campgrounds", first["sha"], "joey")
            with pytest.raises(PermissionError):
                concepts.worded(draws_store, "campgrounds", "my words", "joey")
        assert concepts.picked(draws_store, "campgrounds") is None
        assert concepts.own_wording(draws_store, "campgrounds") is None
        concepts.pick(draws_store, "campgrounds", first["sha"], "joey")
        assert concepts.picked(draws_store, "campgrounds") == first["sha"]
        concepts.pick(draws_store, "campgrounds", None, "joey")
        assert concepts.picked(draws_store, "campgrounds") is None
        started = []  # his pick starts its scene inventory reading, a process of its own in the pick's store
        log = web.reading_started(draws_store, "campgrounds", "joey",
                                  start=lambda argv, **named: started.append((argv, named)))
        [(argv, named)] = started
        assert argv[-5:] == ["-m", "score.review.reading", "campgrounds", "--by", "joey"] and named["start_new_session"]
        assert named["env"]["SCORE_SPEND_STORE"] == str(draws_store.cache.parent) and log.endswith(".log")
        with monkeypatch.context() as reading_now:
            reading_now.setattr(web, "reading_started", lambda store, place, by: started.append((place, by)) or "log")
            assert web.concept_pick(draws_store, "campgrounds", first["sha"], "joey")["library"] == "library: stand-in"
            assert started[1:] == [("campgrounds", "joey")]  # no yes asked
            assert "reading" not in web.concept_pick(draws_store, "campgrounds", None, "joey") and len(started) == 2
        with monkeypatch.context() as library:  # a pick handed to the library by its own concept command
            from score.stages.library import backend
            library.setattr(concepts, "handed_over", HANDED_OVER)
            library.setattr(backend, "settings", lambda: {"SCORE_LIB_ROOT": str(tmp_path / "lib"),
                                                          "SCORE_LIB_COMMAND": "score-lib",
                                                          "SCORE_LIB_BLOBS_DIR": str(tmp_path / "blobs")})
            ran = []

            def lib(words, **named):
                ran.append((words, named))
                said = {"place": "campgrounds", "did": "locked", "address": "concept/campgrounds@1",
                        "saved": {"committed": "c" * 40, "pushed": True, "why": ""}}
                return subprocess.CompletedProcess(words, 0, json.dumps(said) + "\n", "")
            assert concepts.handed_over(draws_store, "campgrounds", run=lib) == "library: locked concept/campgrounds@1"
            words, named = ran[0]
            assert words[:4] == ["score-lib", "--root", str(tmp_path / "lib"), "concept"]
            assert words[words.index("--place") + 1] == "campgrounds" and words[words.index("--world") + 1] == "world1"
            assert words[words.index("--store") + 1] == str(draws_store.objects.root)
            assert named["env"]["SCORE_LIB_BLOBS_DIR"] == str(tmp_path / "blobs")
            assert named["cwd"] == str(tmp_path / "lib")
            refused = lambda words, **named: subprocess.CompletedProcess(words, 1, "", "no SCORE store\n")  # noqa: E731
            assert concepts.handed_over(draws_store, "campgrounds", run=refused) == "not in the library: no SCORE store"
            library.setattr(backend, "settings", lambda: {"SCORE_LIB_BACKEND": "none"})
            assert concepts.handed_over(draws_store, "campgrounds", run=lib).startswith("not in the library: no library")

        # the layers: a place drawn only once the one above is picked, read and planned and holds it
        ready, waiting = concepts.undrawn(draws_store, ["base", "hub", "street"])
        assert ready == ["base"]
        assert waiting == {"hub": "waits for base's concept to be locked",
                           "street": "waits for square's concept to be locked"}
        said_yes(draws_store, patched, "hub")
        with pytest.raises(concepts.Refused, match="hub waits for base's concept to be locked"):
            concepts.draw(draws_store, "hub", {}, "joey", caller=stand_in([]))
        assert concepts.draws(draws_store, "hub") == []
        base = picked_draw(draws_store, patched, "base", (200, 10, 10))
        assert concepts.waits(draws_store, "hub") == "waits for base's scene inventory to be read"
        patched.setattr(reading, "reading_of", lambda store, place: {"stand-in": place})
        assert concepts.waits(draws_store, "hub") == "waits for base's plan to be made"
        patched.setattr(concepts, "plan_made", lambda store, place: True)
        assert concepts.waits(draws_store, "hub") == "waits for base's plan to lay it out"
        ready_above(patched)
        assert concepts.waits(draws_store, "hub") is None and "hub" in concepts.undrawn(draws_store, ["hub"])[0]
        said_yes(draws_store, patched, "hub")
        hub_draw = concepts.draw(draws_store, "hub", {}, "joey", caller=stand_in([]))
        with monkeypatch.context() as remade:
            remade.setattr(concepts, "plan_made", lambda store, place: False)  # the plan above is made again
            with pytest.raises(concepts.Refused, match="hub waits for base's plan to be made"):
                concepts.pick(draws_store, "hub", hub_draw["sha"], "joey")
            said_yes(draws_store, remade, "hub")
            with pytest.raises(concepts.Refused, match="hub waits for base's plan to be made"):
                concepts.draw(draws_store, "hub", {"base": hub_draw["sha"], "note": "x"}, "joey", caller=stand_in([]),
                              reviser=prompt_stand_in([]))
            assert concepts.step_refusal(draws_store, "hub", "read") == "its concept is not locked"
            assert concepts.step_refusal(draws_store, "base", "read") is None
            remade.setattr(reading, "reading_of", lambda store, place: None)
            assert concepts.step_refusal(draws_store, "base", "plan") == "its scene inventory is not read"

        said_yes(draws_store, patched, "lab")  # within another: the crop of its picked holder first, its wording
        asked = []
        lab = concepts.draw(draws_store, "lab", {}, "joey", caller=stand_in(asked))
        wording, sizes = asked[0]
        assert sizes == [(32, 20)] and lab["picks"] == {"base": base}  # only the crop of what holds it
        assert wording.startswith("The black angular spaceship (picture 1) is divided into these compartments: "
                                  "1. hub, ")
        assert "This concept is number 8: lab. " + concepts.INSIDE_ONLY in wording
        assert "1. a crop of the base's picked concept: the black angular spaceship, which holds it" in wording
        assert concepts.current_draw(draws_store, "lab", concepts.wording_now(draws_store, "lab"))
        said_yes(draws_store, patched, "lab")  # a mark on the picture above reaches both calls, that picture boxed
        asked, prompted = [], []
        marked_above = [{"on": "base", "x": 0.7, "y": 0.0, "w": 0.3, "h": 0.3, "note": "this is the lab: its dome"}]
        redrawn = concepts.draw(draws_store, "lab", {"base": lab["sha"], "context_marks": marked_above, "note": ""},
                                "joey", caller=stand_in(asked), reviser=prompt_stand_in(prompted))
        said = "Box P1 (top right of the picked concept of the base): this is the lab: its dome."
        assert said in prompted[0][0] and said in asked[0][0]
        assert len(prompted[0][1]) == len(asked[0][1]) == 3  # the draw boxed and clean, the base's pick boxed
        assert "image 3 is the picked concept of the base" in asked[0][0]
        assert redrawn["context_marks"][0]["on"] == "base"
        said_yes(draws_store, patched, "lab")
        with pytest.raises(concepts.Refused, match="no locked concept"):
            concepts.draw(draws_store, "lab", {"base": lab["sha"],
                                               "context_marks": [{**marked_above[0], "on": "square"}]},
                          "joey", caller=stand_in([]), reviser=prompt_stand_in([]))
        assert concepts.current_draw(draws_store, "lab", concepts.wording_now(draws_store, "lab"))
        picked_draw(draws_store, patched, "base", (10, 200, 10))  # a new pick above: the lab's draw out of date
        assert not concepts.current_draw(draws_store, "lab", concepts.wording_now(draws_store, "lab"))
        assert concepts.undrawn(draws_store, ["base", "lab"])[0] == ["lab"]

        with monkeypatch.context() as quarters:  # a reference from the place's data waits while it is not here
            quarters.setattr(concepts, "picked", lambda _store, place: "abc" if place == "hangar" else None)
            quarters.setattr(concepts, "inputs_of", lambda place: {"references": [
                {"picture": "{home}/references/quarters.png", "shows": "its look only"}]} if place == "quarters" else {})
            assert "is not on this machine" in concepts.waits(draws_store, "quarters")  # the owner's quarters picture
            Image.new("RGB", (8, 8)).save(draws_home / "references" / "quarters.png")
            assert concepts.waits(draws_store, "quarters") is None
            sources = [source for _, source in concepts.sent_pictures(draws_store, "quarters")]
            assert sources == [("crop", "hangar", [0, 0, 32, 20]), draws_home / "references/quarters.png"]
            assert concepts.generated(draws_store, "quarters").endswith(
                "Style: 2099 space base, moon base, mars base, SpaceX-type rockets, Chinese and American mixed.")

        ready_above(patched, box=(16, 10, 32, 20))  # the ship's rooms: one compartment block, only the ship's crop
        picked_draw(draws_store, patched, "hangar", (90, 90, 90))
        with monkeypatch.context() as inventory:  # the holding row's name on the reading above
            inventory.setattr(reading, "reading_of", lambda store, place: {"inventory": {"rows": [
                {"id": "holder", "name": "black angular spaceship"}]}})
            assert holder_words(draws_store, "cockpit") == "the black angular spaceship"
        for room in SHIP_ROOMS:  # the owner, 2026-10-21: no window view, no picture of its own, only the crop
            sources = [source for _, source in concepts.sent_pictures(draws_store, room)]
            assert sources == [("crop", "hangar", [16, 10, 32, 20])], room
        assert concepts.sent_picture(draws_store, ("crop", "hangar", [16, 10, 32, 20])).size == (16, 10)
        blocks = {room: concepts.generated(draws_store, room).split(" This concept is number ")[0]
                  for room in SHIP_ROOMS}
        assert len(set(blocks.values())) == 1  # every sibling the identical block
        assert blocks["cockpit"].startswith("The black angular spaceship (picture 1) is divided into these "
                                            "compartments: 1. cockpit and nav (flying and navigating the ship), 2. ")
        assert "7. walkway (the corridor joining every room" in blocks["cockpit"]
        galley = concepts.generated(draws_store, "galley")
        assert "This concept is number 4: galley. " + concepts.INSIDE_ONLY in galley
        assert "window" not in galley.replace(concepts.INSIDE_ONLY, "")

        square = picked_draw(draws_store, patched, "square", (200, 10, 10))  # the place it opens into, once picked
        ready_above(patched)
        assert concepts.sent_picks(draws_store, "flat") == {"square": square}  # the stairwell not picked: not sent
        said_yes(draws_store, patched, "stairwell")
        concepts.pick(draws_store, "stairwell", concepts.draw(draws_store, "stairwell", {}, "joey",
                                                              caller=stand_in([]))["sha"], "joey")
        words = [words for words, _ in concepts.sent_pictures(draws_store, "flat")]
        assert words[0] == "a crop of the square's picked concept: the black angular spaceship, which holds it"
        assert words[1] == "the stairwell, picked: match the door they share"  # no view through its balcony door
        said_yes(draws_store, patched, "flat")
        asked = []
        flat_draw = concepts.draw(draws_store, "flat", {}, "joey", caller=stand_in(asked))
        assert len(asked[0][1]) == 2 and set(flat_draw["picks"]) == {"square", "stairwell"}
        assert "2. the stairwell, picked: match the door they share" in asked[0][0]
        assert concepts.current_draw(draws_store, "flat", concepts.wording_now(draws_store, "flat"))
        said_yes(draws_store, patched, "stairwell")
        concepts.pick(draws_store, "stairwell", concepts.draw(draws_store, "stairwell", {}, "joey",
                                                              caller=stand_in([1]))["sha"], "joey")
        assert not concepts.current_draw(draws_store, "flat", concepts.wording_now(draws_store, "flat"))
        patched.delenv("SCORE_SPEND_TICKET")

    # the environment concept: his locked version is what every draw reads, and only he keeps one
    shown = ec.current(store, WORLD, ["campgrounds", "hangar", "cockpit", "hub", "launch"])  # today's data, locked
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
    bucket = runtime_store.FolderStore(tmp_path / "bucket")
    monkeypatch.setattr(ec, "PROPS_HOME", tmp_path / "home")
    with pytest.raises(ec.Refused, match="locked"):  # a reference only while he has it unlocked
        ec.referenced(store, WORLD, a_picture(), "dock.png", "the dock's look", "hangar", "joey", offsite=bucket)

    ask = {"topic": "setting", "answer": "Only the Sun and Mars, the camp on Mars",
           "concept": ec.prefilled(["campgrounds"])}  # an ask: only inside his yes, its fields checked by the table
    asked = []

    def model(question, pictures):
        asked.append((question, pictures))
        return ('```json\n{"setting": {"bodies": [{"body": "sun", "name": "Sun", "reference": "sun"}, {"body": '
                '"mars", "name": "Mars", "reference": "mars", "radius_km": 220}], "sites": [{"place": "campgrounds", '
                '"on": "mars", "latitude": 30, "longitude": 130}]}}\n```')
    with pytest.raises(compute.Refused):
        ec.ask(store, WORLD, ask, "joey", reviser=model)
    yes_key = said_yes_to(store, monkeypatch)
    proposal = ec.ask(store, WORLD, ask, "joey", reviser=model)
    mars = proposal["proposed"]["setting"]["bodies"][1]
    assert proposal["yes"] == yes_key and mars["radius_km"] == 3389.5 and mars["gravity"] == 3.728  # not 220
    assert proposal["proposed"]["setting"]["sites"][0]["on"] == "mars"
    assert "the camp on Mars" in asked[0][0] and ec.question_of("setting") in asked[0][0]
    assert ec.asks(store, WORLD) == [proposal]
    with pytest.raises(ec.Refused, match="no JSON"):
        ec.ask(store, WORLD, ask, "joey", reviser=lambda question, pictures: "I think Mars.")
    monkeypatch.setattr(ec, "ask_euros", lambda: 0.05)  # his Send writes its yes at the price shown, then asks

    def run(argv, env, **kwargs):  # the ask's own process, here in-process with the stand-in model
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        sent = ec.ask(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1],
                      reviser=lambda question, pictures: '{"style": "Bright and clean"}')
        return subprocess.CompletedProcess(argv, 0, json.dumps(sent) + "\n", "")
    style_ask = {"topic": "style", "answer": "brighter", "concept": ec.prefilled([])}
    sent = web.environment_ask(store, WORLD, style_ask, 0.05, "joey", run=run)
    sent_yes = store.spend_yes("override", sent["yes"])
    assert sent_yes["by"] == "joey" and sent_yes["euros"] == 0.05 and "environment concept" in sent_yes["purpose"]
    assert sent["proposed"] == {"style": "Bright and clean"}
    assert "not today's measured price" in refusal(
        lambda: web.environment_ask(store, WORLD, style_ask, 0.04, "joey", run=run))
    refusal(lambda: web.environment_ask(store, WORLD, style_ask, 0.05, "runner", run=run))

    first = drawn(store, monkeypatch)  # drawn under today's data, picked; his Unlock puts both out of date
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

    kept = ec.referenced(store, WORLD, a_picture(), "my dock!.png", "the dock's look", "hangar", "joey",
                         offsite=bucket)  # unlocked: a new reference goes to the bucket and its local copy
    assert kept["concept"]["references"][-1] == {"picture": "{home}/references/my-dock-.png",
                                                 "shows": "the dock's look", "place": "hangar"}
    index = json.loads(bucket.read_bytes("references/index.json"))
    assert bucket.exists(index["my-dock-.png"]["key"]) and (tmp_path / "home/references/my-dock-.png").is_file()
    with pytest.raises(ec.Refused, match="no picture"):
        ec.referenced(store, WORLD, b"not a picture", "x.png", "", None, "joey", offsite=bucket)
    with pytest.raises(ec.Refused, match="already named"):
        ec.referenced(store, WORLD, a_picture((1, 2, 3)), "my dock!.png", "", None, "joey", offsite=bucket)
    for off_shape in ({"style": "x" * (ec.LONGEST_LINE + 1)},  # a concept out of shape is refused, a kept one trimmed
                      {"setting": {"bodies": [{"name": "Moon", "radius_km": "heavy"}]}}):
        with pytest.raises(ec.Refused):
            ec.saved(store, WORLD, off_shape, True, "joey")
            pytest.fail(f"taken: {off_shape}")
    trimmed = ec.saved(store, WORLD, {"places": [{"name": " Dock ", "holds": "Bay, Office ,"}]}, False, "joey")
    assert trimmed["concept"]["places"] == [{"name": "Dock", "holds": ["Bay", "Office"]}]

    ec.saved(store, WORLD, ec.prefilled(["campgrounds"]), True, "joey")  # locked again: a new version
    with pytest.raises(concepts.Refused, match="another environment concept"):
        concepts.pick(store, "campgrounds", first["sha"], "joey")
    again = drawn(store, monkeypatch)
    assert again["environment"] == ec.version(store)
    concepts.pick(store, "campgrounds", again["sha"], "joey")
    assert concepts.picked(store, "campgrounds") == again["sha"]
    mine = ec.prefilled(["campgrounds"])  # his own locked version: every draw reads its style and references
    mine["style"] = "Cold steel and ice, a frontier mine."
    mine["references"].append({"picture": "{home}/references/mine.png", "shows": "the pit's look",
                               "place": "campgrounds"})
    ec.saved(store, WORLD, mine, True, "joey")
    assert concepts.style(store) == "Style: Cold steel and ice, a frontier mine."
    assert "Cold steel and ice" in concepts.generated(store, "campgrounds")
    assert concepts.references_of(store, "campgrounds") == [{"picture": "{home}/references/mine.png",
                                                             "shows": "the pit's look"}]
    assert concepts.references_of(store, "street") == []
    assert concepts.waits(store, "campgrounds").startswith("its reference")  # not on this machine
    concepts.recorded(store, f"{ec.AREA}/before-settings/versions/20261021T000000.000000+0000.json", {
        "world": "before-settings", "locked": True, "by": "joey", "at": "2026-10-21T00:00:00+00:00",
        "concept": {"style": "x", "physics": [{"world": "Moon"}], "references": [], "places": []}})
    found = ec.newest(store, "before-settings")["concept"]  # a version kept before settings reads today's setting
    assert "physics" not in found and found["setting"] == setting.now() == ec.setting_of(store, "before-settings")

    # the environment plan: each top scene where his setting puts it, shaped by its own plan, its sky worked out
    with monkeypatch.context() as patched:
        sites_store, shown = Store.in_folder(tmp_path / "sites"), {}
        patched.setattr(plans, "current", lambda store, place: {"plan": shown[place]} if place in shown else None)
        daylight = {"square": True, "wreck": False}  # a daylight concept's sun brought up, a dark one's not
        patched.setattr(reading, "concept_light", lambda store, place: {"rows": {}, "scene": {
            "daylight": daylight[place], "unseen": False, "unseen_colour": ""}} if place in daylight else None)
        today = ec.setting_of(sites_store)
        moon = {"base": BASE, **{place: {"w": 20.0, "d": 20.0} for place in ("square", "wreck", "old_station",
                                                                              "campgrounds")}}
        wide = {**moon, "base": {"w": 110.0, "d": 110.0}}  # wider than the 57 m to the wreck

        def moved(sites, place, **where):
            return [{**site, **where} if site["place"] == place else site for site in sites]
        his = moved(today["sites"], "old_station", longitude=0.0005)  # his own move of the old station, 34 m south
        farm = {**HOUSE, "sites": [*HOUSE["sites"], {"place": "shed", "on": "meadow", "x": 8.0, "y": 0.0,
                                                     "height_m": 0}]}
        two_grounds = {**HOUSE, "plots": [*HOUSE["plots"], {"name": "Yard", "gravity": 9.81}],
                       "sites": [*HOUSE["sites"], {"place": "barn", "on": "yard", "x": 0.0, "y": 0.0, "height_m": 0}]}
        clear = 6.0 + 2.0 + environment_plan.CLEAR_M  # half the house, half the shed and the lane between
        cases = [  # (id, world, his setting kept (None: nothing kept), the scenes' plans shown, what the plan shows)
            ("today's setting, nothing kept", None, None, moon, {
                "sites": {"earth": ["square"], "moon": ["wreck", "old_station", "base"], "mars": ["campgrounds"]},
                "radius": {"moon": 1737400.0},  # the Moon's true radius, never the game's 220 m ball
                "latlon": {"base": (55.0, 0.0)}, "size": {"base": [60.0, 50.0, 15.0]},
                "apart": {("old_station", "base"): pytest.approx(62.5, abs=0.5)},
                "gaps": ["Base: no scene time"], "never": ["place on its ground", "one spot"]}),
            ("the wreck without a plan", None, None, {**moon, "wreck": None}, {
                "size": {"wreck": None}, "gaps": ["Wreck: no plan yet"]}),
            ("a base wider than the 57 m to the wreck", None, None, wide, {
                "latlon": {"base": (55.0, 0.0)}, "never": ["overlap"], "far": {("wreck", "base"): 75.0},
                "clear_of": ("base", ["wreck", "old_station"], 55.0 + 10.0 + environment_plan.CLEAR_M)}),
            ("his first: the physics' proposal, cleared like any", None, today, wide, {"never": ["overlap"]}),
            ("his own move of the old station", None, {**today, "sites": his}, wide, {
                "latlon": {"old_station": (54.999165, 0.0005)}, "latitude_not": {"base": 55.0},
                "never": ["overlap"]}),
            ("two of his own that overlap", None, {**today, "sites": moved(his, "base", latitude=55.0,
                                                                           longitude=0.0005)}, wide, {
                "gaps": ["Old station and Base overlap on Moon: move one in the physics"]}),
            ("his old station stacked on the base", None,
             {**today, "sites": moved(today["sites"], "old_station", latitude=55.0, longitude=0.0)}, moon, {
                "gaps": ["Old station and Base stand on one spot of Moon"]}),
            ("his old station 1.7 km east", None,
             {**today, "sites": moved(today["sites"], "old_station", latitude=55.0, longitude=0.1)}, moon, {
                "apart": {("old_station", "base"): pytest.approx(1737400 * 0.1 * 0.01745329 * 0.573576, rel=1e-3)},
                "east": ("old_station", "base")}),
            ("a house on a plot", None, HOUSE, {"house": {"w": 12.0, "d": 9.0}}, {
                "sites": {"meadow": ["house"]}, "radius": {"meadow": None}, "at": {"house": [0.0, 0.0]},
                "flat": ["house"]}),
            ("a new environment's shed without a plan", NEW, farm, {"house": {"w": 12.0, "d": 9.0}}, {
                "at": {"shed": [8.0, 0.0]}, "gaps": ["Shed: no plan yet"]}),  # the physics' spot
            ("its plan lands 8 m from a 12 m house", NEW, farm, {"house": {"w": 12.0, "d": 9.0},
                                                                "shed": {"w": 4.0, "d": 4.0}}, {
                "at": {"house": [0.0, 0.0], "shed": [clear, 0.0]},
                "exact_gaps": ["House: no scene time", "Shed: no scene time"]}),
            ("his own move of the shed", NEW, {**farm, "sites": [farm["sites"][0], {**farm["sites"][1], "x": 5.0}]},
             {"house": {"w": 12.0, "d": 9.0}, "shed": {"w": 4.0, "d": 4.0}}, {  # the house steps aside
                "at": {"shed": [5.0, 0.0], "house": [5.0 - clear, 0.0]}}),
            ("sites on different grounds", NEW, two_grounds, {"house": {"w": 30.0, "d": 30.0},
                                                              "barn": {"w": 30.0, "d": 30.0}}, {
                "at": {"house": [0.0, 0.0], "barn": [0.0, 0.0]}, "never": ["overlap", "one spot"]}),
        ]
        derived = {}
        for case, world, his_setting, shown_now, expect in cases:
            shown.clear()
            shown.update({place: found for place, found in shown_now.items() if found is not None})
            if his_setting is not None:
                ec.saved(sites_store, world or environment_plan.world_name(),
                         {**ec.prefilled([]), "setting": his_setting}, True, "joey")
            plan = derived[case] = environment_plan.derived(sites_store, world)
            assert sites_of(plan) == expect.get("sites", sites_of(plan)), case
            for found in plan["maps"]:
                assert found["radius_m"] == expect.get("radius", {}).get(found["on"], found["radius_m"]), case
                count = len(found["sites"])  # every pair of sites on a ground measured, one stack named a gap
                assert len(found["distances"]) == count * (count - 1) // 2, (case, found["on"])
                if not any("one spot" in gap for gap in expect.get("gaps", [])):
                    assert all(apart["metres"] >= environment_plan.SAME_SPOT for apart in found["distances"]), case
            for place, at in expect.get("at", {}).items():
                assert site_in(plan, place)["at"] == at, (case, place)
            for place, latlon in expect.get("latlon", {}).items():
                assert (site_in(plan, place)["latitude"], site_in(plan, place)["longitude"]) == latlon, (case, place)
            for place, latitude in expect.get("latitude_not", {}).items():  # stepped aside from the setting's spot
                assert site_in(plan, place)["latitude"] != latitude, (case, place)
            for place, size in expect.get("size", {}).items():
                assert site_in(plan, place)["size"] == size, (case, place)
            for place in expect.get("flat", []):
                assert {spot[2] for spot in site_in(plan, place)["terrain"]["spots"]} == {0.0}, (case, place)
            for gap in expect.get("gaps", []):
                assert gap in plan["gaps"], (case, plan["gaps"])
            assert not [gap for gap in plan["gaps"] if any(word in gap for word in expect.get("never", []))], case
            assert plan["gaps"] == expect.get("exact_gaps", plan["gaps"]), case
            apart = {(found["from"], found["to"]): found["metres"] for world_map in plan["maps"]
                     for found in world_map["distances"]}
            for pair, metres in expect.get("apart", {}).items():
                assert apart[pair] == metres, (case, pair)
            for pair, metres in expect.get("far", {}).items():  # the page's distances follow
                assert apart[pair] > metres, (case, pair)
            if "east" in expect:  # due east, that far on its map
                one, two = expect["east"]
                assert site_in(plan, one)["at"][0] - site_in(plan, two)["at"][0] == pytest.approx(
                    apart[expect["east"]], rel=1e-3), case
            if "clear_of" in expect:  # the larger stands where the physics puts it, the rest just clear, no more
                still, movers, metres = expect["clear_of"]
                for mover in movers:  # along their own bearings
                    assert bearing_from(plan, still, mover) == pytest.approx(
                        bearing_from(derived[cases[0][0]], still, mover), abs=1e-3), (case, mover)
                    off = [abs(site_in(plan, mover)["at"][axis] - site_in(plan, still)["at"][axis]) for axis in (0, 1)]
                    assert max(off) == pytest.approx(metres, abs=0.05), (case, mover)

        free = derived[cases[0][0]]  # today's environment 1: a site's shape its plan's, its ground's bodies
        base = site_in(free, "base")
        assert base["footprint"] == [[-30.0, -25.0], [30.0, -25.0], [30.0, 25.0], [-30.0, 25.0]]  # about its middle
        blocks = {block["name"]: block for block in base["blocks"]}
        assert set(blocks) == {"hub", "hangar", "RADIO MAST"}  # its child scenes by place, a standing thing; no tracks
        assert blocks["hangar"]["tall"] == 15.0 and blocks["hub"]["roof"] == "dome"
        assert blocks["hub"]["points"][0] == [-10.0, -5.0]  # at its hold, in site metres
        assert base["overhead"] is None  # no time yet: a gap
        assert min(spot[2] for spot in base["terrain"]["spots"]) > -0.02  # 100 m on the Moon: all but flat
        assert {body["body"] for body in free["setting"]["bodies"]} == {"sun", "earth", "moon", "mars"}

        # one plan written under the allowance, then his edit of it: fixed facts kept, its sky worked out
        shown.clear()
        shown.update(moon)
        kept_setting(sites_store, today)
        patched.setattr(plan_writing, "call_euros", lambda found: 0.07)
        free, asked, clears = environment_plan.derived(sites_store), [], []

        def ask(body):
            asked.append(body)
            return {"candidates": [{"finishReason": "STOP",
                                    "content": {"parts": [{"text": json.dumps(answer_of(free))}]}}]}, 2.0

        def clear(store, places, euros, node):
            clears.append((node, places))
            return compute.reading_clearance(store, places, euros, node=node)
        record = environment_plan.write(sites_store, "the allowance", ask=ask, clear=clear)
        world_plan = record["plan"]
        assert clears == [(compute.PLAN_WRITING, [f"environment-{environment_plan.world_name()}"])]
        assert record["euros"] == 0.07 and '"radius m": 1737400.0' in asked[0]["contents"][0]["parts"][0]["text"]
        assert world_plan["gaps"] == [] and world_plan["time"] == "2099-06-01T12:00:00Z"
        base, square = site_in(world_plan, "base"), site_in(world_plan, "square")
        assert base["size"] == [60.0, 50.0, 15.0] and base["latitude"] == 55.0  # its plan's shape, the setting's place
        assert square["size"] == [20.0, 20.0, 0.0] and square["blocks"] == []  # a written size or block never stands
        earth = next(body for body in base["overhead"]["bodies"] if body["body"] == "earth")
        assert 1.75 < earth["across"] < 2.05 and earth["altitude"] > 0  # from the Moon's near side: about 1.9 degrees
        assert [50.0, 0.0, -3.5] in site_in(world_plan, "wreck")["terrain"]["spots"]
        bad = environment_plan.write(sites_store, "the allowance", ask=lambda body: ({"candidates": []}, 1.0),
                                     clear=clear)  # a refused answer: no plan, the written one still shown
        assert bad["refused"] and environment_plan.current(sites_store)["how"] == "written"
        shown["square"] = {"w": 29.0, "d": 29.0, "shapes": {"FLOODLIGHT TOWER": {"tall": 18.0}}}
        assert environment_plan.site_of(sites_store, "square")["size"] == [29.0, 29.0, 18.0]  # read again, not kept
        shown["square"] = moon["square"]

        plan = environment_plan.current(sites_store)["plan"]  # his edit of the written plan, settled again
        for world_map in plan["maps"]:
            for site in world_map["sites"]:
                site.update({"time": "2099-06-01T20:00:00Z", "latitude": 1.0, "size": [1.0, 1.0, 1.0]})
        record = environment_plan.edited(sites_store, plan, "joey")
        shown_plan = environment_plan.current(sites_store)
        assert shown_plan["how"] == "edited" and shown_plan["plan"] == record["plan"] and record["plan"]["gaps"] == []
        square = environment_plan.site_of(sites_store, "square")
        assert square["on"] == "earth" and square["latitude"] == 22.28  # where it stands is the setting's
        assert square["size"] == [20.0, 20.0, 0.0]  # its size its plan's
        assert square["written_time"] == "2099-06-01T20:00:00Z" and square["time"] == "2099-06-01T22:00:00Z"
        assert square["overhead"]["lights"][0]["altitude"] > 0  # the Sun up, the hour before it still under
        assert environment_plan.sun_up(shown_plan["plan"]["setting"], square, "2099-06-01T21:00:00Z") is False
        wreck = environment_plan.site_of(sites_store, "wreck")
        assert wreck["time"] == "2099-06-01T20:00:00Z" and "written_time" not in wreck  # no daylight: as written
        daylight["square"] = False  # read again as dark: back to the time written, 4 in the morning in Hong Kong
        square = environment_plan.site_of(sites_store, "square")
        assert square["time"] == "2099-06-01T20:00:00Z" and square["overhead"]["lights"][0]["altitude"] < 0
        with pytest.raises(environment_plan.Refused):
            environment_plan.edited(sites_store, {"maps": "none"}, "joey")
        kept_setting(sites_store, today, locked=False)  # unlocked: a new version puts his edit out of date
        assert environment_plan.current(sites_store)["how"] == "derived"

        shown.clear()  # the house on its plot, timed: its rooms keep its sky, kept once and dropped when out of date
        shown["house"] = {"w": 12.0, "d": 9.0}
        house_plan = timed(sites_store, NOON)
        assert site_in(house_plan, "house")["overhead"]["bodies"] == [] and site_in(
            house_plan, "house")["overhead"]["lights"][0]["altitude"] == pytest.approx(38.0, abs=0.01)
        found = scene_sky.sky_of(house_plan, "kitchen", "house")  # a room keeps its top scene's site and time
        assert found["top"] == "house" and found["time"] == NOON
        assert found["site"] == {"on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}
        sun = overhead.seen(found["setting"], found["site"], found["time"])["lights"][0]
        assert sun["altitude"] == pytest.approx(90.0 - 52.0, abs=0.01) and sun["azimuth"] == pytest.approx(
            180.0, abs=0.01)
        assert scene_sky.sky_of(house_plan, "barn", "barn") is None  # no site on the plan
        assert scene_sky.keep(sites_store, ["house"]) == (["house"], ["house"])  # its sky kept, written once
        kept = json.loads((scene_sky.KEPT / "house.json").read_text())
        assert kept["place"] == kept["top"] == "house" and kept["setting"]["lights"][0]["name"] == "Sun"
        assert scene_sky.keep(sites_store, ["house"]) == (["house"], [])
        timed(sites_store, None)  # a new version of the physics: the timed plan out of date, the derived one untimed
        assert scene_sky.keep(sites_store, ["house"]) == ([], ["house"])
        assert not (scene_sky.KEPT / "house.json").exists()

    # the plan review in a store of its own, a holder `yard` holding `shed`: no plan before the inventory counts, a
    # holder with no outline of its own given one round its inside places, his edits kept as his own and checked and
    # sent with a Correct that has no note, the plan stage reading his plan and dropping it once the pick goes, a
    # correction only inside his yes, a scene he added in the app or a parent scene with no data a place once its design
    # is done, listed before the scenes it holds
    with monkeypatch.context() as planned:
        plan_store, plan_folder = Store.in_folder(tmp_path / "plans"), tmp_path / "plan-review"
        data = plan_data(plan_store, plan_folder, planned)
        kept = plan_folder / "kept/shed.json"
        assert plans.current(plan_store, "shed") is None  # not picked: no inventory counts
        assert plans.holder_of(plan_store, "shed") is None and not plans.made(plan_store, "yard")
        # a holder with no outline of its own (the base): the shed, 6 x 6 m with no plan of its own, is inside it
        assert plans.outline_from_inside(plan_store, "yard") == (6.6, 6.6)
        assert reading.outline_of(plan_store, "yard") == (6.6, 6.6)  # the reading sizes its rows against it
        assert reading.outline_of(plan_store, "nowhere") is None
        picked(plan_store, "yard")  # the pick is the approval: its inventory read, its plan is made
        assert plans.current(plan_store, "yard")["plan"]["w"] == 6.6 and plans.made(plan_store, "yard")
        plans.name_inside(plan_store, "yard", ["Tool Hut"], "joey")
        inside = plans.current(plan_store, "yard")["plan"]["holds"]
        assert [hold["place"] for hold in inside] == ["shed", "tool_hut"]
        assert inside[0]["w"] == 6.0  # no plan of its own
        _, path = plans.shape_sent(plan_store, "shed")[0]
        assert Image.open(path).size[0] > 100
        assert plans.holder_of(plan_store, "shed") == {"holder": "yard", "row": None, "box": None, "view": None,
                                                       "outline": [0.3, 0.3, 6.0, 6.0]}  # the yard's own ground
        picked(plan_store, "shed")
        shown = plans.current(plan_store, "shed")
        plan = shown["plan"]
        # no filed plan (retired 2026-10-21): a bare one in its room on the plan above, 6 x 6 m with no plan of its own
        assert shown["how"] == "derived" and (plan["w"], plan["d"]) == (6.0, 6.0) and plan["doors"] == []
        names = {item[0]: item for item in plan["items"]}
        assert plan["rows"]["BENCH 1"] == ["bench", "vice"] and plan["rows"]["CRATE 2"] == ["crate"]
        assert names["BENCH 1"][1:5] == [2.0, 1.7, 2.0, 0.6]  # laid at its spot: its middle 1 m south of the room's
        assert plan["rows"][plan_checks.WALLS_ITEM] == ["lamp"]
        assert plan["people"] == [[3.0, 3.0]]
        assert plan["elements"][0] == {"element": "a bench", "rows": ["bench"]}

        asked = []  # a correction runs only inside his yes, and one with no note and no edit of his is refused first

        def gemini(question, pictures):
            asked.append((question, len(pictures)))
            return 'Here: {"people": [[1.0, 1.0]]}'

        request = {"marks": [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "stand by the bench"}], "note": ""}
        with pytest.raises(compute.Refused):
            plans.revised(plan_store, "shed", request, "joey", reviser=gemini)
        planned.setattr(plans, "revise_euros", lambda: 0.05)
        bare = {"marks": [], "context_marks": [], "note": ""}
        with pytest.raises(plans.Refused, match="no note to correct the plan by"):
            web.plan_revise(plan_store, "shed", bare, 0.05, "joey", run=None)  # nothing changed: no yes written
        assert not list((plan_store.cache / plans.AREA / "asked").glob("*.json")) and asked == []

        fixed_twice = ["bench: stood", "bench: moved 0.00 m", "bench: stood"]  # a writing re-fixed: a fix said again
        written(plan_store, "shed", {**plan, "doors": [["S", 2.0, 0.9, "DOOR to the yard"]], "fixes": fixed_twice})
        assert plans.current(plan_store, "shed")["plan"]["fixes"] == fixed_twice[:2]  # each fix said once
        assert plans.keep(plan_store, ["shed", "yard"]) == (["shed"], ["shed"])  # the yard's only derived: none kept
        before, shown = kept.read_bytes(), plans.current(plan_store, "shed")["plan"]
        plans.kept_for_stage(plan_store, "shed", {
            **dict(reversed(shown.items())), "fixes": fixed_twice, "notes": ["words"],
            "gaps": [{"kind": "size", "item": "BENCH 1", "words": "other words"}]})
        assert kept.read_bytes() == before  # notes alone, in another key order: the kept plan as it was, not re-keyed
        plans.kept_for_stage(plan_store, "shed", {**shown, "people": [[3.5, 2.0]]})
        assert json.loads(kept.read_text())["people"] == [[3.5, 2.0]]  # a thing moved: kept anew
        plans.kept_for_stage(plan_store, "shed", shown)
        kept_plan = json.loads(kept.read_text())
        assert kept_plan == {**plans.current(plan_store, "shed")["plan"],
                             "concept": {**kept_plan["concept"], "pick": PICK}}
        assert kept_plan["concept"]["picture"] == "{home}/design/concepts/shed.png"  # the picked concept, its input
        assert (plan_folder / "kept-concepts/shed.png").read_bytes() == plan_store.objects.read_bytes(f"blobs/{PICK}")
        assert json.loads((plan_folder / "kept-inventory/shed.json").read_text())["rows"][0]["id"] == "bench"
        plan = plans.current(plan_store, "shed")["plan"]
        plan["people"] = [[3.0, 2.0]]
        plans.edited(plan_store, "shed", plan, "joey")
        assert json.loads(kept.read_text())["people"] == [[3.0, 2.0]]  # his edit, kept for the stage at once
        plan = plans.current(plan_store, "shed")["plan"]
        plan["items"][0][1] = 0.5
        plan["doors"][0] = ["E", 1.0, 0.9, "moved"]
        plans.edited(plan_store, "shed", plan, "joey")
        shown = plans.current(plan_store, "shed")
        assert shown["how"] == "edited" and shown["plan"]["items"][0][1] == 0.5
        assert shown["plan"]["doors"][0] == ["E", 1.0, 0.9, "DOOR to the yard"]  # moved, its words kept
        with pytest.raises(plans.Refused, match="keeps its doors"):
            plans.edited(plan_store, "shed", {**plan, "doors": []}, "joey")
        with pytest.raises(plans.Refused, match="not a number"):
            plans.edited(plan_store, "shed", {**plan, "items": [["X", "far", 0, 1, 1, None, "item"]]}, "joey")
        note = plans.note_of(plan_store, "shed", bare)  # a Correct with no note sends his kept edits
        assert note.startswith("I changed the plan by hand: item ") and plan["items"][0][0] in note
        assert plans.note_of(plan_store, "shed", {**bare, "note": "wider door"}) == "wider door"

        def run(argv, env, **named):
            planned.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
            record = plans.revised(plan_store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], reviser=gemini)
            return subprocess.CompletedProcess(argv, 0, json.dumps({"how": record["how"]}) + "\n", "")

        assert web.plan_revise(plan_store, "shed", request, 0.05, "joey", run=run) == {"how": "revised"}
        assert asked[0][1] == 2 and "stand by the bench" in asked[0][0]
        assert plans.newest_edit(plan_store, "shed")["plan"]["people"] == [[1.0, 1.0]]  # kept as answered
        assert math.dist(plans.current(plan_store, "shed")["plan"]["people"][0], [1.0, 1.0]) < 0.1  # out of the wall
        with pytest.raises(review.Refused, match="not today's measured price"):
            web.plan_revise(plan_store, "shed", request, 0.04, "joey", run=run)
        concepts.pick(plan_store, "shed", None, "joey")  # unlocked: no plan counts, the stage's copies dropped
        assert plans.current(plan_store, "shed") is None
        assert plans.keep(plan_store, ["shed"]) == ([], ["shed"]) and not kept.exists()
        assert not (plan_folder / "kept-inventory/shed.json").exists()
        assert not (plan_folder / "kept-concepts/shed.png").exists()

        # a child scene he added on a plan (no file of it in the data) is a scene in design, no place, until its concept
        # is locked, its inventory read and its plan written or edited; then the build lists it and its plan row reads
        # its kept plan (owner, 2026-10-21)
        plan = plans.current(plan_store, "yard")["plan"]
        plans.edited(plan_store, "yard", {**plan, "holds": [*plan["holds"], {**plan["holds"][0], "place": "hut",
                                                                             "x": 0.0}]}, "joey")
        world = graph.Environment("world1", 3, {"data": str(data)})
        assert stages.places(world, plan_store) == ["yard"]  # the shed and the hut in design: their concepts not locked
        picked(plan_store, "hut")
        shown = plans.current(plan_store, "hut")
        assert shown["how"] == "derived" and stages.places(world, plan_store) == ["yard"]  # its plan not written
        assert plans.keep(plan_store, ["hut"]) == ([], []) and not stages.plan_written("hut")
        plans.edited(plan_store, "hut", shown["plan"], "joey")
        assert stages.places(world, plan_store) == ["yard", "hut"]
        assert plans.keep(plan_store, ["hut"]) == (["hut"], []) and (plan_folder / "kept/hut.json").is_file()
        assert stages.plan_written("hut") and stages.PLAN.files("hut")["plan"] == "{home}/design/plans/{place}.json"
        # a parent scene holding others with no file of its own in the data (the Moon base, a shell) is a place once its
        # design is done, listed before the scenes it holds, its plan kept where the plan stage and the scene tree read
        (data / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"},
                                                                        "yard": {"within": "farm"}},
                                                             "shells": {"farm": {"name": "Farm"}}}))
        assert stages.places(world, plan_store) == ["yard", "hut"]  # the farm in design: no place yet
        picked(plan_store, "farm")
        shown = plans.current(plan_store, "farm")
        assert shown["how"] == "derived" and [hold["place"] for hold in shown["plan"]["holds"]] == ["yard"]
        assert stages.places(world, plan_store) == ["yard", "hut"]  # its plan not written
        plans.edited(plan_store, "farm", shown["plan"], "joey")
        assert stages.places(world, plan_store) == ["farm", "yard", "hut"]  # the parent scene first
        assert plans.keep(plan_store, ["farm"]) == (["farm"], []) and (plan_folder / "kept/farm.json").is_file()
        # a spot takes its child scene's own plan size, centred where it sat, and says so (owner, 2026-10-25: "the
        # framework should be able to solve [it] agnosticly"): the yard he edits to a 30 m plan, its held shed moved to
        # a spot of it and a cart beside, the shed locked again with his edits back and then written 4 x 10 m
        # the yard's 30 m plan asks plan_fixes.offsets for its 42.4 m reach on every item it brings inside: one grid of the
        # same nine million offsets each time, 3.6 s apiece, made once here (the function is pure, its answer only read)
        planned.setattr(plan_fixes, "offsets", functools.lru_cache(maxsize=2)(plan_fixes.offsets))
        plan = plans.current(plan_store, "yard")["plan"]
        shed_hold = next(hold for hold in plan["holds"] if hold["place"] == "shed")
        plan["w"] = plan["d"] = 30.0
        plan["holds"] = [{**shed_hold, "x": 10.0, "y": 10.0}]
        plan["items"] = [["CART 1", 13.0, 7.5, 1.0, 1.0, None, "item"]]  # clear of the spot, not of the shed's own size
        written(plan_store, "yard", {**plan, "items": [], "holds": []})  # its own 30 x 30 m, which his edit keeps
        plans.edited(plan_store, "yard", plan, "joey")
        held = plans.current(plan_store, "yard")["plan"]
        assert held["holds"][0]["w"] == 6.0 and not [gap for gap in held["gaps"] if gap["kind"] == "held"]
        plan_store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "b" * 64, "at": "2026-10-20T00:00",
                                                        "room": held["holds"][0]})  # drawn on the spot as it was
        concepts.pick(plan_store, "shed", PICK, "joey")  # locked again: its reading and his edits back with it
        assert plans.newest_edit(plan_store, "shed")["plan"]["people"] == [[1.0, 1.0]]  # the Correct he sent, kept
        plans.edit_replaced(plan_store, "shed", "joey", {"words": "Replace my edit", "question": "Replace?",
                                                         "at": "2026-11-04T14:00"})
        written(plan_store, "shed", {**plans.current(plan_store, "shed")["plan"], "w": 4.0, "d": 10.0})
        fitted = plans.current(plan_store, "yard")["plan"]
        assert {key: fitted["holds"][0][key] for key in "xywd"} == {"x": 11.0, "y": 8.0, "w": 4.0, "d": 10.0}
        assert fitted["items"][0][1:5] == [13.0, 7.0, 1.0, 1.0]  # pushed north off the shed, the shortest way
        assert [gap["item"] for gap in fitted["gaps"] if gap["kind"] == "held"] == ["shed", "CART 1"]
        assert plans.moved_draws(plan_store, "shed") == set()  # its own size is no move of its room
        # each held spot's judging, the shed's own 4 x 10 m plan read from this store where a row names it
        for row_name, function, arguments, want in HELD_SPOTS:
            arguments = [plan_store if argument is THE_STORE else argument for argument in arguments]
            if isinstance(want, Refusal):
                with pytest.raises(plans.Refused, match=want):
                    function(*arguments)
                    pytest.fail(f"{row_name}: taken")
            else:
                answer = function(*arguments)
                assert holds(answer, want), (row_name, answer)
        # its drawing is asked at its own proportions in a square frame, never its spot's shape (#72: the flat drawn to
        # the Square's thin strip of it)
        wording = plan_drawing.wording_of(plan_store, "shed")
        assert "not its shape" in wording and "filling exactly" not in wording and plan_drawing.FRAME == "1:1"
        # an open place held by another is drawn as its own ground alone, a room is not (the street drawn as its shops'
        # rooms and the Square's corner, outlined as the whole frame, 2026-11-04)
        for inside in (True, False):
            planned.setattr(plan_drawing.concepts, "indoors", lambda plan_store, place, inside=inside: inside)
            assert (plan_drawing.OPEN in plan_drawing.wording_of(plan_store, "shed")) is not inside
        assert "never round a building's rooms" in plan_writing.ASKED
        # a prefix walk gives the keys a whole-plan_store walk gives, a part of a folder's name too
        for prefix in ("concepts/", "concepts/sh", "plans/shed/", "nothing/"):
            assert concepts.keys_under(plan_store, prefix) == plan_store.objects.keys(prefix)
        # an open place with a shape is told its strip's metres and the way it runs in its drawing's wording
        planned.setattr(plan_drawing.plans, "creator_shape", lambda place, path=None: {"w": 8.0, "d": 36.0})
        assert "36 m from north to south, its long side running north to south" in plan_drawing.wording_of(plan_store, "shed")
        # his edit replaced by its writing on his yes in chat: the plan shown is the one made without him again
        assert plans.current(plan_store, "yard")["how"] == "edited"
        plans.edit_replaced(plan_store, "yard", "an agent, on his yes", {"words": "Replace my edit", "question": "Replace?",
                                                                     "at": "2026-11-04T14:15"})
        assert plans.newest_edit(plan_store, "yard") is None and plans.current(plan_store, "yard")["how"] != "edited"
        # his edit's things past its own outline are brought inside it when it is shown (the hangar's 2026-10-21 edit kept
        # a 55.7 m writing's spots and crates past its 32 x 64 m), each fix said; the edit itself is kept as he made it
        edit = {**plans.current(plan_store, "yard")["plan"], "w": 30.0, "d": 30.0, "holds": [],
                "items": [["CART 1", 29.8, 20.0, 1.0, 1.0, None, "item"]], "people": [[34.0, 10.0]]}
        plans.edited(plan_store, "yard", edit, "joey")
        shown = plans.current(plan_store, "yard")["plan"]
        assert shown["items"][0][1:5] == [29.0, 20.0, 1.0, 1.0] and 29.0 <= shown["people"][0][0] < 30.0, shown["people"]
        assert len(shown["fixes"]) == len(edit.get("fixes", [])) + 2 and plans.newest_edit(plan_store, "yard")["plan"]["items"][0][1] == 29.8
        # a free redrawing under his standing word on design fixes (#72: the base's tube drawn as its 3.2 m section): kept
        # as an edit with its reason, shown; a field no drawing has, or no reason, refused
        asked = {"words": "design fixes following his rules are ours", "at": "2026-11-05T03:00", "reason": "its section"}
        for changes, given, said in (({"concept": {}}, asked, "not concept"),
                                     ({"w": 5.0}, {**asked, "reason": ""}, "its reason")):
            with pytest.raises(plans.Refused, match=said):
                plans.redrawn(plan_store, "shed", changes, "an agent", given)
        record = plans.redrawn(plan_store, "shed", {"w": 5.0, "openings": [door([0.0, 2.0], "yard")], "people": [[7.0, 2.0]],
                                               "doors": [["W", 2.0, 2.2, "HATCH W 2.2 x 2.66 m"]],
                                               "leads": {"W": {"to": "yard", "why": "the yard"}}}, "an agent", asked)
        assert record["how"] == "redrawn" and record["asked"]["reason"] == "its section" and record["changed"] == [
            "doors", "leads", "openings", "people", "w"]
        shown = plans.current(plan_store, "shed")  # what it lays past its outline brought inside, as his edit's is
        assert (shown["how"], shown["plan"]["w"], shown["plan"]["d"]) == ("redrawn", 5.0, 10.0), shown["how"]
        # and each doorway its own door rows say shown at its row's width where it is drawn, the edit kept as made (habitat's
        # edit of 2026-10-25 kept its writing's 0.237 m hatches for its 2.2 m rows, the greenhouse's redrawing a 1.305 m one)
        assert [(opening["at"], opening["wide"]) for opening in shown["plan"]["openings"]] == [([0.0, 2.0], 2.2)] and \
            record["plan"]["openings"][0]["wide"] == 0.9, shown["plan"]["openings"]
        assert shown["plan"]["people"][0][0] < 5.0 and record["plan"]["people"] == [[7.0, 2.0]], shown["plan"]["people"]
        # and a person spot standing in a thing on a floor of its shell moved out of it, the thing kept where drawn
        # (greenhouse's redrawing of 2026-11-05 kept astronaut_2 in its grow light frame on its lower floor, 2026-11-08)
        framed = [{"id": "frame", "anchor": "on:deck", "size": [2.0, 2.0, 2.0], "count": 1, "at": []},
                  {"id": "astronaut", "noun": "astronaut", "count": 1, "size": [0.6, 0.6, 1.8], "at": []},
                  {"id": "stove", "count": 2, "size": [0.6, 0.6, 0.9], "at": []}]
        picked(plan_store, "bay", framed)
        redrawn = {**plans.current(plan_store, "bay")["plan"], "w": 6.0, "d": 6.0, "structure": ["deck"], "holds": [],
                   "items": [["FRAME 1", 2.0, 2.0, 2.0, 2.0, None, "item"], ["STOVE 1", 5.0, 0.5, 0.6, 0.6, None, "item"],
                             ["STOVE 2", 5.2, 0.6, 0.6, 0.6, None, "item"]], "people": [[3.0, 3.0, 0.0, "astronaut"]],
                   "rows": {"FRAME 1": ["frame"], "STOVE 1": ["stove"], "STOVE 2": ["stove"]},
                   "shapes": {"STOVE 1": {"shape": "rect", "tall": 0.9, "base": 0.0},
                              "STOVE 2": {"shape": "rect", "tall": 0.9, "base": 0.9}}}
        written(plan_store, "bay", {**redrawn, "people": []})
        plans.edited(plan_store, "bay", redrawn, "joey")
        shown = plans.current(plan_store, "bay")["plan"]
        assert not (1.75 < shown["people"][0][0] < 4.25 and 1.75 < shown["people"][0][1] < 4.25) and shown["items"][0][1:5] == [
            2.0, 2.0, 2.0, 2.0] and plans.newest_edit(plan_store, "bay")["plan"]["people"][0][:2] == [3.0, 3.0], shown["people"]
        # and its second stove piled on its first stood on the floor beside it (flat's redrawing of 2026-11-05, settle@flat
        # in env1 checkout 68), the edit kept as made
        assert shown["shapes"]["STOVE 2"]["base"] == 0.0 and shown["items"][2][1:3] != [5.2, 0.6] and \
            plans.newest_edit(plan_store, "bay")["plan"]["shapes"]["STOVE 2"]["base"] == 0.9, shown["items"]
        # a writing's doorway to a sibling held once whose own plan leads none back leads nowhere, said; one the sibling's
        # door meets, or a lead of its own names, stays (the Square's street, written again with an opening to the
        # stairwell, whose own street gate leads outside since its edit: plan@square's held gate, 2026-11-06)
        (data / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"},
                                                                        "barn": {"within": "yard"}}, "shells": {}}))
        plans.edited(plan_store, "yard", {**edit, "holds": [
            {"place": "shed", "row": None, "x": 0.0, "y": 0.0, "w": 5.0, "d": 10.0},
            {"place": "barn", "row": None, "x": 10.0, "y": 0.0, "w": 4.0, "d": 4.0}]}, "joey")
        picked(plan_store, "barn", [{"id": "cart", "name": "a cart", "anchor": "floor", "size": [1.0, 1.0, 1.0],
                                     "count": 1, "at": []}])
        barn = {**plans.current(plan_store, "barn")["plan"], "w": 4.0, "d": 4.0, "leads": {},
                "openings": [door([0.0, 1.0], "shed"), door([4.0, 1.0], "yard")]}
        written(plan_store, "barn", barn)
        shown = plans.current(plan_store, "barn")["plan"]
        assert [opening["to"] for opening in shown["openings"]] == [None, "yard"], shown["openings"]
        assert shown["fixes"][-1] == "the door at [0.0, 1.0] to shed leads nowhere: no door of shed's own plan leads back " \
                                     "to barn", shown.get("fixes")
        # a writing's doorway to a name that is no place of the design nor a row of its inventory leads nowhere, said; one
        # to a row of its inventory, a place of the tree or sealed stays (the street's door to 'restaurant', 2026-11-07)
        written(plan_store, "barn", {**barn, "openings": [*barn["openings"], door([2.0, 0.0], "kitchen"),
                                                     door([2.0, 4.0], "cart"), door([1.0, 4.0], "sealed")]})
        shown = plans.current(plan_store, "barn")["plan"]
        assert [opening["to"] for opening in shown["openings"]] == [None, "yard", None, "cart", "sealed"], \
            shown["openings"]
        assert "the door at [2.0, 0.0] to 'kitchen' leads nowhere: no place of the design nor a row of its inventory" in \
            shown["fixes"], shown.get("fixes")
        written(plan_store, "barn", {**barn, "leads": {"W": {"to": "shed"}}})  # a fixed door: left for the gate to show
        assert [opening["to"] for opening in plans.current(plan_store, "barn")["plan"]["openings"]] == ["shed", "yard"]
        written(plan_store, "barn", barn)
        yard_holds = plans.current(plan_store, "yard")["plan"]["holds"]
        plans.edited(plan_store, "yard", {**edit, "holds": [yard_holds[0], {**yard_holds[1], "leads": {"shed": "pipe#1"}}, {
            "place": "pipe", "row": None, "x": 5.0, "y": 0.0, "w": 5.0, "d": 2.0, "instance": "pipe#1"}]}, "joey")
        # its hold leads it to pipe#1: judged there, never by shed's own plan (the base's airlock door to the hub, led to
        # tube#3: plan@base's held gate, 2026-11-06)
        assert [opening["to"] for opening in plans.current(plan_store, "barn")["plan"]["openings"]] == ["shed", "yard"]
        plans.edited(plan_store, "yard", {**edit, "holds": yard_holds}, "joey")
        plans.redrawn(plan_store, "shed", {"openings": [door([5.0, 1.0], "barn")]}, "an agent", asked)
        assert [opening["to"] for opening in plans.current(plan_store, "barn")["plan"]["openings"]] == ["shed", "yard"]

    # the yard's rooms in a store of its own, read with rows of its own: what the reading lays and leaves a gap, the
    # shed's room as his locks, the writings and the redrawings leave it and as his edits move it, the rooms his
    # edit holds by rows, a shared room with things in it, and a room merged away
    with monkeypatch.context() as roomed:
        rooms = Store.in_folder(tmp_path / "rooms")
        data = plan_data(rooms, tmp_path / "plan-rooms", roomed)
        rooms.write_once("concepts/yard/draws/1.json", {"place": "yard", "sha": PICK, "at": "2026-10-21T00:00"})
        concepts.pick(rooms, "yard", PICK, "joey")  # picked, not read yet: no inventory, no plan
        assert plans.current(rooms, "yard") is None and not plans.made(rooms, "yard")
        read(rooms, "yard", ROOM_ROWS, at="2026-10-21T00:01", size=[100, 50])
        plan = plans.current(rooms, "yard")["plan"]
        assert plan["rows"]["BARN 1"] == ["barn", "bell"]  # a row on its parent's
        assert {item[0]: item[1:5] for item in plan["items"]} == {
            "ROCK 1": [0.3, 0.3, 1.0, 1.0],  # a box but no metres: SAM 3 gives where, never size
            "BARN 1": [1.6, 0.3, 3.0, 2.0],  # its metres, laid after the rock, whose box stands left of its: a box
            "CART 1": [0.3, 2.6, 1.5, 1.0],  # orders, it is never projected (owner, 2026-10-21); the cart's metres
            "WELL 1": [2.1, 2.6, 1.0, 1.0],  # a size in words: 1 m
            "SHIP 1": [3.4, 2.6, 1.0, 1.0], "CRANE 1": [4.7, 2.6, 1.0, 1.0], "LOFT 1": [0.3, 3.9, 1.0, 1.0]}
        assert [gap["words"] for gap in plan["gaps"]] == ["Rock 1: no size", "Well 1: no size"]
        room = plans.room_of(rooms, "shed")
        assert room == {"place": "shed", "row": None, "x": 0.3, "y": 0.3, "w": 6.0, "d": 6.0}
        # the shed's draws: one on its room as recorded, a Redraw of it with notes, one from before rooms were
        # recorded
        rooms.write_once("concepts/shed/draws/1.json", {"place": "shed", "sha": PICK, "at": concepts.now(),
                                                        "room": room})
        concepts.pick(rooms, "shed", PICK, "joey")
        rooms.write_once("concepts/shed/draws/2.json", {"place": "shed", "sha": "c" * 64, "base": PICK,
                                                        "at": concepts.now()})
        rooms.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "d" * 64, "at": "2026-10-01T00:00"})
        assert not concepts.plan_changed(rooms, "shed") and plans.moved_draws(rooms, "shed") == set()
        # a plan written again (its inventory read again) never moves a locked scene's room (owner, 2026-10-21: "get
        # my concepts back ... i had alr locked them"), nor does a free redrawing (a design fix under his standing
        # word, #72) that moves and turns it: 2026-11-05, the base's and the square's redrawings put every held lock
        # out of date
        moved = {**plan, "holds": [{**room, "x": 0.0, "w": 6.6}]}
        written(rooms, "yard", moved)
        assert plans.current(rooms, "yard")["how"] == "written" and plans.room_of(rooms, "shed") == room
        assert not concepts.plan_changed(rooms, "shed")
        asked = {"words": "design fixes following his rules are ours", "at": "2026-11-05T03:00", "reason": "its doors"}
        turned = {**room, "x": room["x"] + 1.0, "turn": 45}
        plans.redrawn(rooms, "yard", {"holds": [turned]}, "an agent", asked)
        assert plans.room_of(rooms, "shed")["turn"] == 45 and not concepts.plan_changed(rooms, "shed")
        concepts.pick(rooms, "shed", "d" * 64, "joey")  # locked on a draw from before rooms were recorded
        assert not concepts.plan_changed(rooms, "shed")  # a writing since moves no locked room
        plans.redrawn(rooms, "yard", {"holds": [{**turned, "y": room["y"] + 1.0}]}, "an agent", asked)
        assert not concepts.plan_changed(rooms, "shed")  # nor a redrawing since
        # his edit does (owner, 2026-10-21: a move or resize of a room on the plan above means the room is drawn again):
        # he sizes the rock and the well and narrows the shed's room
        plan["items"] = [[*item[:3], 2.0, 2.0, *item[5:]] if item[0] in ("ROCK 1", "WELL 1") else item
                         for item in plan["items"]]
        plans.edited(rooms, "yard", {**plan, "holds": [{**room, "d": 5.0}]}, "joey")
        assert concepts.plan_changed(rooms, "shed")
        assert plans.moved_draws(rooms, "shed") == {PICK, "c" * 64, "d" * 64}  # the older one: a plan above made since
        assert plans.current(rooms, "yard")["plan"]["gaps"] == []  # he sized them: their gaps are gone
        assert plans.removed(rooms, plans.within_file()[0]) == []
        written(rooms, "yard", moved)
        shown = plans.current(rooms, "yard")
        assert shown["how"] == "edited" and shown["plan"]["holds"][0]["d"] == 5.0  # his edit over a newer writing
        assert shown["plan"]["gaps"][-1]["kind"] == "edited"
        concepts.pick(rooms, "shed", "d" * 64, "joey")  # locked again on his edit's room
        plans.redrawn(rooms, "yard", {"holds": [{**room, "d": 5.0, "turn": 90}]}, "an agent", asked)
        assert not concepts.plan_changed(rooms, "shed")  # a redrawing after his lock moves it no more
        # his inside places and rows: a room adjoining rooms a row holds is held by that row over one it only
        # overlaps (owner, 2026-10-21: the docking airlock just behind the engine room, its box over the crane, "is
        # still part of the ship"); a room its row names or on its own floor keeps its own; a row's box is its
        # holder's, the surest of a reading's boxes
        plan = shown["plan"]
        spot = {"x": 2.0, "y": 2.0, "w": 4.0, "d": 3.0}
        plan["holds"] = [{**spot, "place": "shed", "row": "ship"},
                         {**spot, "place": "cabin", "row": "ship", "y": -1.0},
                         {**spot, "place": "dock", "row": "crane", "x": 3.0, "y": 5.15, "w": 2.0},  # 0.15 m behind it
                         {**spot, "place": "loft", "row": "loft", "x": 6.1},  # beside it, its own row by its name
                         {**spot, "place": "hut", "row": None, "y": 5.0, "x": 0.0, "w": 1.0},
                         {"place": "attic", "row": "barn", "x": 12.0, "y": 0.3, "w": 6.0, "d": 6.0}]
        held = {hold["place"]: hold["row"] for hold in plans.edited(rooms, "yard", plan, "joey")["plan"]["holds"]}
        assert held == {"shed": "ship", "cabin": "ship", "dock": "ship", "loft": "loft", "hut": None, "attic": "barn"}
        assert plans.tree(rooms)["within"] == dict.fromkeys(held, "yard")  # his edit's holds are what follows
        assert plans.holder_of(rooms, "shed") == {"holder": "yard", "row": "ship", "box": [70, 20, 95, 45],
                                                  "view": "v1", "outline": [2.0, 2.0, 4.0, 3.0]}
        assert plans.holder_of(rooms, "attic")["box"] == [10, 10, 60, 35]  # its surest SAM box
        # the concept review reads the same: the attic's draw waits on the yard, its holder now, read and planned
        assert concepts.above("attic", rooms) == "yard" and concepts.inside_of("yard", rooms) == list(held)
        assert concepts.step_refusal(rooms, "attic", "draw") is None
        assert plans.made(rooms, "yard") and concepts.holding_row(rooms, "shed") == "ship"
        with pytest.raises(plans.Refused, match="no inventory row"):
            plans.edited(rooms, "yard", {**plan, "holds": [{**plan["holds"][0], "row": "silo"}]}, "joey")
        # two rooms overlapped on the plan above are one shared room named from both; the add-scene box dropped inside
        # a room is a thing kept with that room, no scene of its own, named with its spot in the room's draw wording;
        # either changes the room, so its draws are drawn again (owner, 2026-10-21). A room he left alone stays as it
        # was.
        plans.name_inside(rooms, "yard", ["tool hut"], "joey")
        plan = plans.current(rooms, "yard")["plan"]
        shed = plans.room_of(rooms, "shed")
        plans.edited(rooms, "yard", plan, "joey")  # kept as laid: no key added to a room he did not touch
        assert plans.room_of(rooms, "shed") == shed
        rooms.write_once("concepts/shed/draws/3.json", {"place": "shed", "sha": "e" * 64, "at": concepts.now(),
                                                        "room": shed})
        assert "e" * 64 not in plans.moved_draws(rooms, "shed")
        merged = {**shed, "w": 8.0, "d": 3.0, "name": "Shed and tool hut",
                  "things": [{"name": "workbench", "x": 3.0, "y": 1.0, "w": 2.0, "d": 1.0},
                             {"name": "lathe", "x": 6.5, "y": 0.2, "w": 1.0, "d": 0.6}]}
        plans.edited(rooms, "yard", {**plan, "holds": [merged]}, "joey")
        assert plans.tree(rooms)["within"] == {"shed": "yard"}  # the tool hut no scene any more, nor rooms left out
        assert plans.room_of(rooms, "shed")["things"][0] == {"name": "workbench", "x": 3.0, "y": 1.0, "w": 2.0,
                                                             "d": 1.0}
        assert plans.moved_draws(rooms, "shed") == {PICK, "c" * 64, "d" * 64, "e" * 64}
        assert concepts.room_name(rooms, "shed") == "shed and tool hut"
        assert concepts.thing_words(rooms, "shed") == ("Standing in it: workbench in the middle; lathe in the "
                                                       "north-east corner.")
        assert plans.room_edits(plan, plans.current(rooms, "yard")["plan"])[0] == \
            "made the scene shed one shared room called Shed and tool hut"
        with pytest.raises(plans.Refused, match="has no name"):
            plans.edited(rooms, "yard", {**plan, "holds": [{**merged, "things": [{"x": 1, "y": 1, "w": 1, "d": 1}]}]},
                         "joey")
        # a place the plan no longer lays out is removed, never an outside place, and has no stage line
        concepts.pick(rooms, "shed", PICK, "joey")
        read(rooms, "shed", PLAN_ROWS["shed"])
        plans.edited(rooms, "shed", plans.current(rooms, "shed")["plan"], "joey")  # its design done: a place
        world = graph.Environment("world1", 3, {"data": str(data)})
        assert stages.places(world, rooms) == ["yard", "shed"]  # the scene tree's order: the parent scene first
        plans.edited(rooms, "yard", {**plan, "holds": []}, "joey")  # merged away
        assert plans.removed(rooms, plans.within_file()[0]) == ["shed"]
        assert stages.places(world, rooms) == ["yard"]  # the build follows him: no stage line for it

    # the sync pass's plans keep (plans_pass.main) over one store's written places: a free re-fix of a settled-by-it
    # writing made before the keep and outside its moment (parted only where its plan row stands unaccepted, people
    # spaced either way), a re-fix that may ask Corrects left to a process of its own, the keep inside one moment over
    # the narrow walk, and a done place with no kept plan given one. Each writing below is a place of the world:
    # habitat and airlock: six sandbags in one spot, fixed once (habitat's plan row accepted, airlock's not, review of
    # 2026-10-26); galley and hold: the same never fixed (hold's row accepted); plaza: fixed before rows at the
    # concept's foot were brought in from beyond (airlock, 2026-10-26); bay: a bag laid again in its own row's run
    # (settle@airlock, 2026-11-09, its row accepted); lock: a Correct's copies of a person and spots standing in a wall,
    # a crate and each other (airlock, 2026-10-30; hangar's workers, camp's astronauts), its row accepted
    with monkeypatch.context() as passing:
        cube = [1.0, 1.0, 1.0]
        bags = [[f"SANDBAGS {number}", 1.2, 1.3, 0.6, 0.35, None, "item"] for number in range(1, 7)]
        piled = {"w": 3.0, "d": 3.0, "doors": [], "people": [], "items": bags, "fixes": ["earlier fix"], "gaps": [],
                 "rows": {item[0]: ["sandbags"] for item in bags}}
        sandbags = {"rows": [{"id": "sandbags", "anchor": "ground", "count": 6, "size": [0.6, 0.35, 0.15]}]}
        unfixed = {key: value for key, value in piled.items() if key != "fixes"}
        beyond_items = [["BARREL 1", 1.5, 4.5, 1.0, 1.0, None, "item"], ["BARREL 2", 7.5, 4.5, 1.0, 1.0, None, "item"],
                        ["PALLET 1", 4.5, 7.5, 1.0, 1.0, None, "item"], ["DESK 1", 7.5, 2.5, 1.0, 1.0, None, "item"]]
        beyond = {"w": 10.0, "d": 10.0, "doors": [], "people": [], "items": beyond_items, "structure": ["plates"],
                  "fixes": [], "beyond": ["sandbags"],
                  "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in beyond_items}}
        foot = {"picture": [1000, 1000], "rows": [
            {"id": "plates", "anchor": "ground", "count": 1, "boxes": [[0, 500, 1000, 1000]]},
            {"id": "barrel", "count": 2, "size": cube, "boxes": [[150, 400, 250, 500], [750, 400, 850, 500]]},
            {"id": "pallet", "anchor": "on:plates", "count": 1, "size": cube, "boxes": [[450, 700, 550, 800]]},
            {"id": "desk", "count": 1, "size": cube, "boxes": [[750, 200, 850, 300]]},
            {"id": "sandbags", "anchor": "ground", "count": 1, "size": cube, "boxes": [[450, 900, 550, 1000]]}]}
        doubled = {"w": 6.0, "d": 6.0, "doors": [], "people": [], "fixes": ["earlier fix"], "gaps": [],
                   "items": [["SANDBAGS 1", 1.0, 1.0, 3.0, 0.5, None, "item"],
                             ["SANDBAGS 2", 1.2, 1.1, 0.6, 0.4, None, "item"]],
                   "rows": {"SANDBAGS 1": ["sandbags"], "SANDBAGS 2": ["sandbags"]},
                   "shapes": {"SANDBAGS 1": {"shape": "rect", "tall": 0.2, "base": -0.2, "count": 5},
                              "SANDBAGS 2": {"shape": "rect", "tall": 0.2, "base": -0.2}}}
        sixbags = {"rows": [{"id": "sandbags", "anchor": "ground", "count": 6, "size": [0.6, 0.4, 0.2]}]}
        corners = [[0.0, 0.0], [6.0, 0.0], [6.0, 6.0], [0.0, 6.0], [0.0, 0.0]]
        walls = [{"from": one, "to": other, "thick": 0.2} for one, other in zip(corners, corners[1:])]
        copied = {"w": 6.0, "d": 6.0, "doors": [], "walls": walls, "fixes": ["earlier fix"], "gaps": [],
                  "items": [["CRATE 1", 4.0, 1.0, 1.0, 1.0, None, "item"]], "rows": {"CRATE 1": ["crate"]},
                  "people": [[3.0, 3.0, 0.0, "astronaut"], [3.04, 3.03, 0.0, 1], [3.02, 3.06, 0.0, 1], [0.2, 3.0],
                             [4.5, 1.5], [0.45, 4.5], [3.65, 3.0], [3.3, 3.1], [1.5, 4.5, 0.0, 2], [5.0, 5.0, 0.0, 2]]}
        crew = {"rows": [{"id": "astronaut", "noun": "astronaut", "count": 1, "size": [0.6, 0.6, 1.4]},
                         {"id": "pilot_2", "noun": "person", "count": 1, "size": [0.6, 0.6, 1.8]},
                         {"id": "crate", "count": 1, "size": [1.0, 1.0, 1.0]}]}
        world = {"habitat": (piled, sandbags), "airlock": (piled, sandbags), "galley": (unfixed, sandbags),
                 "hold": (unfixed, sandbags), "plaza": (beyond, foot), "bay": (doubled, sixbags),
                 "lock": (copied, crew)}
        accepted = {f"plan@{place}": "the accepted output" for place in ("habitat", "hold", "bay", "lock")}
        pass_folder = tmp_path / "plans-pass"
        pass_store = Store.in_folder(pass_folder / "store")
        (pass_folder / "kept").mkdir(parents=True)
        (pass_folder / "kept/habitat.json").write_text("{}")  # the one place whose plan is kept for the stage
        seen, kept = [], {}
        passing.setattr(Store, "accepted", lambda self, node: accepted.get(node))
        passing.setattr(plan_writing, "written_of", lambda store, place: {"place": place, "at": "then",
                                                                          "plan": copy.deepcopy(world[place][0])})
        passing.setattr(plans, "inventory_of", lambda store, place: world[place][1])
        passing.setattr(plan_writing, "kept", lambda store, record: seen.append(
            ("kept", record["place"], plans.HELD.get() is None)) or kept.setdefault(record["place"], record))
        passing.setattr(plan_writing, "AUTOMATIC", True)
        passing.setattr(plans, "KEPT", pass_folder / "kept")
        passing.setattr(holders, "KEPT_PLANS", pass_folder / "kept")
        passing.setattr(holders, "KEPT_INVENTORY", pass_folder / "kept-inventory")
        passing.setattr(stages, "places", lambda world_of, store: list(world))
        passing.setattr(plans, "keep", lambda store, places: seen.append(
            ("keep", places, plans.HELD.get() is not None)) or (places, places))
        whole = runtime_store.FolderStore.keys
        passing.setattr(runtime_store.FolderStore, "keys", whole)  # main installs the narrow walk: the whole one after

        def kept_main(argv):
            seen.append(("main", argv, plans.HELD.get() is not None,
                         runtime_store.FolderStore.keys is plans_pass.narrow_keys))
            print("plans for the plan stage: 1 kept")
            return 0
        passing.setattr(plans, "main", kept_main)
        passing.setattr(plans_pass.fixing, "__defaults__",
                        (lambda command, **options: seen.append(("fixing", command)),))
        passing.setenv(compute.STORE, str(pass_folder / "store"))
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            assert plans_pass.main() == 0
        fixing = [event[1] for event in seen if event[0] == "fixing"][0]
        line = said.getvalue()
        assert line.startswith("plans for the plan stage: 1 kept; plans of airlock, bay, lock parted; plans of airlock, "
                               "galley, hold, plaza, bay, lock being fixed: "), line
        assert line.strip().endswith(".log") and fixing[-8:] == [
            "score.review.plans_pass", "fix", "airlock", "galley", "hold", "plaza", "bay", "lock"], fixing
        # the free re-fixes made first, outside the moment; the done places with no kept plan given theirs and the keep
        # run inside it over the narrow walk; then the unsettled ones started in a process of their own
        assert seen[:3] == [("kept", "airlock", True), ("kept", "bay", True), ("kept", "lock", True)], seen
        assert seen[3:] == [("keep", ["airlock", "galley", "hold", "plaza", "bay", "lock"], True),
                            ("main", ["keep"], True, True), ("fixing", fixing)], seen
        assert plans_pass.restored(pass_store) == ["airlock", "galley", "hold", "plaza", "bay", "lock"]
        assert not plans_pass.parting(pass_store, "habitat") and plans_pass.parting(pass_store, "airlock")
        assert plans_pass.refixed(pass_store, "habitat", "test", plans_pass.unasked) is None
        assert all(record["euros"] == 0.0 and record["calls"] == [] for record in kept.values()), kept
        # the pile parted free (no Correct asked for overlaps alone), its earlier fixes kept, and settled
        parted = kept["airlock"]["plan"]
        assert not plans_pass.placing_more(piled, sandbags) and plans_pass.unsettled(piled, sandbags)
        assert parted["fixes"][0] == "earlier fix" and len(parted["fixes"]) >= 6
        assert not [gap for gap in parted["gaps"] if gap["kind"] == "overlap"]
        assert not plans_pass.unsettled(parted, sandbags)
        # the accepted bay's bag laid again in its own row's run taken off before the keep, accepted row or not
        assert not plans_pass.placing_more(doubled, sixbags) and plans_pass.unsettled(doubled, sixbags, False)
        assert [item[0] for item in kept["bay"]["plan"]["items"]] == ["SANDBAGS 1"], kept["bay"]
        # a never-fixed writing's re-fix in its own process, its accepted row's without the solver: nothing asked
        asked = []
        refit, calls = plans_pass.settled_again(None, "hold", {**unfixed, "fixes": []}, sandbags, asked.append,
                                                parts=False)
        assert refit["items"] == unfixed["items"] and calls == [] and asked == []
        # the plaza's rows at the concept's foot, brought in from beyond once fixed again, settle it
        assert plans_pass.unsettled(beyond, foot)
        fixed, fixes = plan_fixes.fixed(beyond, foot)
        assert not plans_pass.unsettled({**fixed, "fixes": fixes}, foot)
        # the lock's copies dropped, one astronaut left; a numbered spot short of its row's count given its row back,
        # one more of that full row a copy; a spot in a wall, the crate or another person moved to the nearest clear
        # floor, one near but clear left where it was placed
        spots = kept["lock"]["plan"]["people"]
        assert not plans_pass.placing_more(copied, crew) and plans_pass.unsettled(copied, crew, parts=False)
        assert len(spots) == 7 and [spot for spot in spots if len(spot) >= 4] == [
            copied["people"][0], [1.5, 4.5, 0.0, "pilot_2"]], spots
        assert spots[3:5] == [[0.45, 4.5], [3.65, 3.0]], spots  # near a wall, near the astronaut: clear, kept
        wall_one, crate_one, person_one = spots[1], spots[2], spots[5]
        assert 0.1 + 0.3 - 0.05 <= wall_one[0] < 0.2 + 0.3 and abs(wall_one[1] - 3.0) < 0.05, wall_one
        assert not (3.75 < crate_one[0] < 5.25 and 0.75 < crate_one[1] < 2.25)
        assert math.dist(crate_one, [4.5, 1.5]) < 0.9
        assert all(abs(person_one[0] - other[0]) >= 0.6 - 0.05 or abs(person_one[1] - other[1]) >= 0.6 - 0.05
                   for other in spots[:5]), spots
        assert not plans_pass.unsettled(kept["lock"]["plan"], crew, parts=False)
        assert len(kept["lock"]["plan"]["fixes"]) == 8, kept["lock"]["plan"]["fixes"]
        # the free search handing back the spot itself (its rounded cell centre) is no move: no fix, the plan settled
        # (2026-11-03: lab and workshop logged "moved 0.00 m" on every sync pass, re-keying terrain and every line)
        with monkeypatch.context() as still:
            still.setattr(standing, "nearest_free", lambda spot, *rest: [spot[0] + 0.0004, spot[1]])
            assert plans_pass.spaced_people({**copied, "people": [[0.2, 3.0]]}, crew) == (
                {**copied, "people": [[0.2, 3.0]]}, [])
        # a floor thing on a floor of the shell (a row of the plan's structure) is stood in too (2026-11-07:
        # greenhouse's astronaut_2 kept in its grow light frame on its lower floor, and the cast left it out)
        on_deck = {"rows": [*crew["rows"][:2], {**crew["rows"][2], "anchor": "on:deck"}]}
        shelled, moved = plans_pass.spaced_people({**copied, "structure": ["deck"], "people": [[4.5, 1.5]]}, on_deck)
        assert moved and not (3.75 < shelled["people"][0][0] < 5.25 and 0.75 < shelled["people"][0][1] < 2.25), shelled
        # the people spaced after what kept_apart changed, so the writing kept is settled, not one more re-fix
        # (airlock's astronaut stood 0.02 m in something once its sandbags were off, re-fixed a pass later)
        shoved = {"w": 6.0, "d": 6.0, "doors": [], "people": [[3.0, 3.0]], "fixes": ["earlier fix"], "gaps": [],
                  "items": [["CRATE 1", 0.5, 0.5, 1.0, 1.0, None, "item"]], "rows": {"CRATE 1": ["crate"]}}
        crates = {"rows": [{"id": "crate", "anchor": "ground", "count": 1, "size": [1.0, 1.0, 1.0]}]}
        # a person standing in a thing alone wants a re-fix, one standing clear of it none
        assert plans_pass.unsettled({**shoved, "people": [[1.0, 1.0]]}, crates, parts=False)
        assert not plans_pass.unsettled({**shoved, "people": [[4.0, 4.0]]}, crates, parts=False)
        with monkeypatch.context() as apart:
            apart.setattr(plan_fixes, "kept_apart", lambda plan, inventory: plan["items"][0].__setitem__(
                slice(1, 3), [2.5, 2.5]) or ["moved"])
            moved_off, calls = plans_pass.settled_again(None, "airlock", shoved, crates, plans_pass.unasked,
                                                        parts=False)
        assert moved_off["items"][0][1:3] == [2.5, 2.5] and not (2.5 < moved_off["people"][0][0] < 3.5 and
                                                                 2.5 < moved_off["people"][0][1] < 3.5), moved_off
        # the narrow walk (main's) answers as the whole store's walk, a partial write left out
        for key in ["outputs/a.json", "outputs/ab/c.json", "outputs/b.json", "plans/x/edits/1.json",
                    "plans/xy/edits/2.json", "blobs/abc", "top.json"]:
            pass_store.objects.write_bytes(key, b"{}")
        pass_store.objects.write_bytes("outputs/half.json.partial", b"")
        for prefix in ("", "outputs/", "outputs/a", "outputs/ab/", "plans/x", "plans/x/", "plans/x/edits/1", "to",
                       "missing/", "missing/deeper/x"):
            assert plans_pass.narrow_keys(pass_store.objects, prefix) == whole(pass_store.objects, prefix), prefix

    # the plan writing in a store of its own, the yard holding the shed and a hut read beside it: no Make plan click
    # spends while the allowance stands, outside it a writing runs only inside his yes at today's price; the shed's
    # writing is a plan of the stage tables' schema, each failed check a named gap, written once unless asked again,
    # his edits checked again; a reading writes its plan on its own only under the allowance; a read place with no plan
    # is owed unless refused, his Make plan writing it again, and an older method's dearer call is no price of today's
    with monkeypatch.context() as writing:
        writing.delenv("SCORE_SPEND_TICKET", raising=False)  # the concept draws' yes is no yes of a writing
        write_store = Store.in_folder(tmp_path / "writing")
        plan_data(write_store, tmp_path / "plan-writing", writing)
        asked, ask = writing_stand_ins(writing)
        picked(write_store, "shed")
        assert plans.current(write_store, "shed")["how"] == "derived"
        assert plan_writing.owed(write_store, ["shed", "yard"]) == ["shed"]  # the yard not read yet
        ran = []

        def clicked(argv, env, **named):  # his Make plan's process, standing in: it prints no record
            ran.append(env)
            return subprocess.CompletedProcess(argv, 0, "", "")

        assert web.plan_write(write_store, "shed", 0.0, "joey", run=clicked) == {"place": "shed", "written": "already"}
        assert ran[0].get("SCORE_SPEND_TICKET", "") == ""  # under the allowance his click is no yes of his

        def made(argv, env, **named):  # his Make plan's process inside his yes: the ticket it is given is its clearance
            writing.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
            record, = plan_writing.write(write_store, [argv[-3]], argv[-1], ask=ask)
            return subprocess.CompletedProcess(argv, 0, plan_writing.said(record) + "\n", "")

        with writing.context() as off:
            off.setattr(plan_writing, "AUTOMATIC", False)
            with pytest.raises(compute.Refused):
                plan_writing.write(write_store, ["shed"], "joey", ask=ask)
            with pytest.raises(web.review.Refused, match="not today's price"):
                web.plan_write(write_store, "shed", 0.09, "joey", run=made)
        assert asked == [] and ran == [ran[0]]  # nothing asked, nothing run

        clears = []
        price = plan_writing.price(write_store)
        record, = plan_writing.write(write_store, ["shed"], "the allowance", clear=clearing(clears), ask=ask)
        assert clears == [(compute.PLAN_WRITING, ["shed"], price)] and record["euros"] == 0.04
        assert record["drawing_euros"] == 0.12 and record["measured"] == {"metres a unit": [0.01, 0.01],
                                                                          "by": "its rows' metres"}
        assert "a bench, 2 a crate" in ask.drawn[0] and len(asked[0]["contents"][0]["parts"]) == 3
        assert plan_writing.spent(write_store, ["shed"]) == 0.16 and plan_writing.price(write_store) == 0.16
        plan = plans.current(write_store, "shed")["plan"]
        assert plans.current(write_store, "shed")["how"] == "written"
        items = {item[0]: item for item in plan["items"]}
        assert items["BENCH 1"] == ["BENCH 1", 1.0, 0.3, 2.0, 0.6, "S", "item"]
        assert plan["rows"]["BENCH 1"] == ["bench", "vice"]  # the vice rides on it, placed by no item of its own
        assert plan["shapes"]["CRATE 1"]["shape"] == "circle" and plan["shapes"]["LAMP 1"]["base"] == 2.0
        # no filed plan names its doors (retired 2026-10-21): its doorway is the answer's opening, leading to the yard
        assert plan["doors"] == [] and [opening["to"] for opening in plan["openings"]] == ["yard"], plan["openings"]
        assert len(plan["walls"]) == 4 and plan["roofs"][0]["top"] == 3.4 and plan["section"] == {"y": 1.5}
        assert [len(opening["points"]) for opening in plan["roofs"][0]["openings"]] == [4], plan["roofs"]  # a roof's hole
        words = [gap["words"] for gap in plan["gaps"]]
        assert {"item": "ghost", "why": "no such row"} in plan["dropped"] and {"item": "walls", "why": "1 off the schema"} \
            in plan["dropped"]  # kept apart: no gap of his
        # the overlap parted before it is shown; the second crate has no box to place it by, so it is left, saying why
        assert words == [f"crate: 2 in the concept, 1 on the plan: {plan_fixes.WHY['placed']}"]
        assert [fix for fix in plan["fixes"] if "moved" in fix and "out of" in fix]
        assert not [word for word in words if "reached" in word or "outside" in word]
        assert plan_writing.write(write_store, ["shed"], "the allowance", clear=clearing(clears), ask=ask) == []  # once
        # asked again (a writing made by a retired measure, #72), it is written again though written
        again, = plan_writing.write(write_store, ["shed"], "the allowance", clear=clearing(clears), ask=ask, again=True)
        assert again["at"] > record["at"] and plan_writing.written_of(write_store, "shed")["at"] == again["at"]
        plan["items"] = [[*item[:2], 0.3, *item[3:]] if item[0] == "CRATE 1" else item for item in plan["items"]]
        plan["items"].append(["CRATE 2", 3.2, 2.0, 0.5, 0.5, None, "item"])
        plan["rows"]["CRATE 2"] = ["crate"]
        plans.edited(write_store, "shed", plan, "joey")
        words = [gap["words"] for gap in plans.current(write_store, "shed")["plan"]["gaps"]]
        assert "bench 1 and crate 1 stand in each other (north)" in words
        assert "crate: 2 in the concept, 1 on the plan" not in words  # his second crate counts
        plan["items"] = [[*item[:2], 2.0, *item[3:]] if item[0] == "CRATE 1" else item for item in plan["items"]]
        plan["items"] = [item for item in plan["items"] if item[0] != "CRATE 2"]
        plans.edited(write_store, "shed", plan, "joey")
        words = [gap["words"] for gap in plans.current(write_store, "shed")["plan"]["gaps"]]
        assert "bench 1 and crate 1 stand in each other (north)" not in words  # his move, checked again

        # a reading writes its plan on its own under the allowance, and nothing with it off
        writing.setattr(plan_writing, "asked", ask)
        picked(write_store, "hut", PLAN_ROWS["shed"])
        assert reading.planned(write_store, ["hut"], "the allowance") == 0
        assert plans.current(write_store, "hut")["how"] == "written"
        picked(write_store, "yard", PLAN_ROWS["shed"])
        with writing.context() as off:
            off.setattr(plan_writing, "AUTOMATIC", False)
            assert reading.planned(write_store, ["yard"], "the allowance") == 0
            assert plan_writing.writings(write_store, "yard") == []
        # a read place with no plan is owed until a writing of it is refused; then only his Make plan writes it again
        assert plan_writing.owed(write_store, ["shed", "yard"]) == ["yard"]
        refused = {"place": "yard", "concept": plans.pick_of(write_store, "yard"), "method": plan_writing.METHOD,
                   "reading": plan_writing.reading_at(write_store, "yard"), "at": "2026-10-21T00:00:00+00:00",
                   "euros": 0.2, "refused": "no plan"}
        plan_writing.kept(write_store, refused)
        assert plan_writing.to_write(write_store, ["yard"]) == ["yard"] and plan_writing.owed(write_store, ["yard"]) == []
        price = plan_writing.price(write_store)
        plan_writing.kept(write_store, {**refused, "method": 1, "at": "2026-10-21T00:00:01+00:00", "euros": 0.9})
        assert plan_writing.price(write_store) == price  # an older method's dearer call is no price of today's
        started = []
        assert plan_writing.started(write_store, ["yard"], start=lambda argv, **named: started.append(argv)).endswith(
            ".log")
        assert started[0][-2:] == ["score.review.plan_writing", "yard"]
        with writing.context() as off:  # his Make plan, outside the allowance: his yes for exactly today's price
            off.setattr(plan_writing, "AUTOMATIC", False)
            assert web.plan_write(write_store, "yard", price, "joey", run=made)["place"] == "yard"
            yes, = [write_store.read(key) for key in write_store.objects.keys("spend-yes/") if "plan-write-yard" in key]
            assert yes["euros"] == price and yes["by"] == "joey"
            assert plans.current(write_store, "yard")["how"] == "written" and plan_writing.owed(write_store, ["yard"]) == []

    monkeypatch.setattr(store, "is_framework_store", lambda: True)  # an agent's process keeps no version or reference
    monkeypatch.setattr(concepts, "running_under_agent", lambda: True)
    monkeypatch.setattr(ec, "running_under_agent", lambda: True)
    with pytest.raises(PermissionError):
        ec.saved(store, WORLD, ec.prefilled([]), False, "joey")
    with pytest.raises(PermissionError):
        ec.kept_reference(a_picture(), "dock.png")


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


# --- Discuss: one call inside his yes, its thread sent to the redraw --------------------------------------------------


def answerer(asked, answer="Make the door red and wider.", euros=0.0271):
    """A prompt model that keeps what it was asked and answers `answer` at `euros`."""
    def answered(question, pictures):
        asked.append((question, [picture.size for picture in pictures]))
        return answer, euros
    return answered


# --- the environment concept's helpers (its checks are in test_the_owners_word_stands) ------------------------------


WORLD = "world1"


def said_yes_to(store, monkeypatch, key="test-yes"):
    review.spend(store, "override", key, 0.05, "joey", purpose="test")
    monkeypatch.setenv("SCORE_SPEND_TICKET", f"override {key}")
    return key


def drawn(store, monkeypatch, place="campgrounds"):
    said_yes_to(store, monkeypatch, concepts.yes_key(place, review.now()))
    return concepts.draw(store, place, {}, "joey", caller=lambda wording, pictures: a_picture(
        (len(concepts.draws(store, place)) * 30, 9, 9)))


# --- the setting: real bodies from the cited table, invented ones whole -----------------------------------------------


SUN = {"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
       "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}


HOUSE = {"bodies": [], "plots": [{"name": "Meadow", "gravity": 9.81}], "lights": [SUN],
         "backdrops": [{"name": "Sky", "lux": 10000}],
         "sites": [{"place": "house", "on": "meadow", "x": 0, "y": "0", "height_m": 0}]}


REFUSED_SETTINGS = [  # (row, a setting off its shape, the refusal's words)
    ("a sun light whose equinox is no moment", {**HOUSE, "lights": [{**SUN, "equinox": "noon"}]},
     "no equinox|equinox is no moment"),
    ("a backdrop of no known shape", {**HOUSE, "backdrops": [{"name": "Sky", "lux": 1, "shape": "box"}]},
     "shape is one of"),
    ("a backdrop sharing the sun light's key", {**HOUSE, "backdrops": [{"name": "Sun", "lux": 1}]}, "share a key"),
    ("an invented star shining with no kelvin", {"bodies": [{"name": "Star", "radius_km": 1, "mass_kg": 1, "lux": 5}]},
     "shines with"),
    ("an invented body with no distance of its own",
     {"bodies": [{"reference": "sun"}, {"name": "Home", "radius_km": 5000, "mass_kg": 5e24, "around": "sun"}]},
     "no distance_km"),
    ("a reference to no real body", {"bodies": [{"reference": "vulcan"}]}, "no real body"),
    ("a site on neither a body nor a plot", {**HOUSE, "sites": [{"place": "house", "on": "the moon", "x": 0, "y": 0}]},
     "no body or plot"),
    ("two bodies orbiting nothing", {"bodies": [{"reference": "sun"}, {"reference": "mars", "around": ""},
                                                {"name": "Star two", "radius_km": 1, "mass_kg": 1}]},
     "orbits nothing"),
    ("a moon round an Earth not there", {"bodies": [{"reference": "sun"}, {"reference": "moon"}]}, "is no body"),
    ("a site at latitude 95", {"bodies": [{"reference": "sun"}, {"reference": "mars"}],
                               "sites": [{"place": "camp", "on": "mars", "latitude": 95, "longitude": 0}]},
     "latitude of 95"),
]


# --- overhead: the sky at a site, against skies known apart from the code ---------------------------------------------


LIT_HOUSE = setting.checked({
    "plots": [{"name": "Meadow", "gravity": 9.81}],
    "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
                "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}],
    "backdrops": [{"name": "Sky", "shape": "dome", "lux": 10000, "kelvin": 9000}],
    "sites": [{"place": "house", "on": "meadow", "x": 0, "y": 0}]})


def above(value, low=None, high=None):
    """A reading strictly between its bounds (an open side None)."""
    return (low is None or value > low) and (high is None or value < high)


SKIES = [  # (row, seen from: a body, latitude, longitude, or "house", the moment, the light or body, field, expected)
    # expected: an exact value, a pytest.approx, or (low, high) strictly between, an open side None
    ("full Moon, 25 January 2024, 17:54 UT", ("earth", 0.0, 0.0), "2024-01-25T18:00:00Z", "moon", "lit", (0.97, None)),
    ("the full Moon is half a degree across", ("earth", 0.0, 0.0), "2024-01-25T18:00:00Z", "moon", "across",
     pytest.approx(0.52, abs=0.04)),
    ("new Moon, 11 January 2024, 11:57 UT", ("earth", 0.0, 0.0), "2024-01-11T12:00:00Z", "moon", "lit", (None, 0.03)),
    ("Greenwich at the equinox: the light is the Sun's", ("earth", 51.48, 0.0), "2024-03-20T12:07:00Z", "light", "of",
     "sun"),
    ("Greenwich at the equinox: the Sun's kelvin", ("earth", 51.48, 0.0), "2024-03-20T12:07:00Z", "light", "kelvin",
     5772.0),
    ("Greenwich at the equinox: the Sun at 90 less the latitude", ("earth", 51.48, 0.0), "2024-03-20T12:07:00Z",
     "light", "altitude", pytest.approx(90 - 51.48, abs=0.5)),
    ("Greenwich at the equinox: the Sun due south", ("earth", 51.48, 0.0), "2024-03-20T12:07:00Z", "light", "azimuth",
     pytest.approx(180, abs=1)),
    ("March: Earth near its mean distance, the Sun at its strength", ("earth", 51.48, 0.0), "2024-03-20T12:07:00Z",
     "light", "lux", pytest.approx(128000, rel=0.02)),
    ("the Sun at perihelion: 32.53 arc minutes", ("earth", 0.0, 0.0), "2024-01-03T00:00:00Z", "light", "across",
     pytest.approx(32.53 / 60, abs=0.005)),
    ("the Sun at aphelion: 31.46 arc minutes", ("earth", 0.0, 0.0), "2024-07-05T00:00:00Z", "light", "across",
     pytest.approx(31.46 / 60, abs=0.005)),
    *((f"Earth from the Moon, 2099-06-{day:02d}: about 1.9 degrees", ("moon", 55.0, 0.0), f"2099-06-{day:02d}T12:00:00Z",
       "earth", "across", (1.75, 2.05)) for day in (1, 8, 15)),
    ("Earth from the Moon at new Earth", ("moon", 55.0, 0.0), "2099-06-01T12:00:00Z", "earth", "lit", (None, 0.1)),
    ("Earth from the Moon a fortnight on: nearly full", ("moon", 55.0, 0.0), "2099-06-15T12:00:00Z", "earth", "lit",
     (0.8, None)),
    ("Mars from Earth is a point", ("earth", 22.3, 114.2), "2099-06-01T12:00:00Z", "mars", "across", (None, 0.01)),
    ("Earth from Mars is a point", ("mars", 30.0, 130.0), "2099-06-01T12:00:00Z", "earth", "across", (None, 0.01)),
    ("the Sun at Mars, 1.38 to 1.67 AU: 128000 over its square", ("mars", 30.0, 130.0), "2099-06-01T12:00:00Z",
     "light", "lux", (45000, 65000)),
    ("a house's sun is a light of no body", "house", "2024-03-20T12:00:00Z", "light", "of", None),
    ("a house's sun at its own lux", "house", "2024-03-20T12:00:00Z", "light", "lux", 100000),
    ("a house's sun at its own kelvin", "house", "2024-03-20T12:00:00Z", "light", "kelvin", 5800),
    ("a house's equinox noon: 90 less its latitude", "house", "2024-03-20T12:00:00Z", "light", "altitude",
     pytest.approx(90 - 52.0, abs=0.01)),
    ("a house's equinox noon: due south", "house", "2024-03-20T12:00:00Z", "light", "azimuth",
     pytest.approx(180, abs=0.01)),
    ("a house's summer noon a quarter year on: at its highest", "house", "2024-06-20T12:00:00Z", "light", "altitude",
     pytest.approx(90 - 52.0 + 23.44, abs=0.3)),
    ("a house's equinox midnight: as far under", "house", "2024-03-21T00:00:00Z", "light", "altitude",
     pytest.approx(-38.0, abs=0.5)),
    ("a house's equinox morning: on the horizon", "house", "2024-03-20T06:00:00Z", "light", "altitude",
     pytest.approx(0.0, abs=0.15)),
    ("a house's equinox morning: due east", "house", "2024-03-20T06:00:00Z", "light", "azimuth",
     pytest.approx(90, abs=0.2)),
]


def sky(bodies, seen_from, when):
    """The sky over a site: from a body of these bodies at a latitude and longitude, or over the lit house's site."""
    if seen_from == "house":
        return overhead.seen(LIT_HOUSE, LIT_HOUSE["sites"][0], when)
    return overhead.from_body(bodies, *seen_from, when)


def thing_in(found, key):
    """The first light of a sky ("light"), or the body of that key in it."""
    if key == "light":
        return found["lights"][0]
    return next(body for body in found["bodies"] if body["body"] == key)


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


# --- each scene's kept sky --------------------------------------------------------------------------------------------


NOON = "2024-03-20T12:00:00Z"


def timed(store, when):
    """The house's environment plan with its scene time set to `when` (None: none), kept as his edit."""
    kept_setting(store, HOUSE)
    plan = environment_plan.derived(store)
    plan["maps"][0]["sites"][0]["time"] = when
    return environment_plan.edited(store, plan, "joey")["plan"]


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


def parted_rows(store, place, folder):
    """stand_in_rows answered with each row's part: the mast a structure, the rest objects."""
    rows, *rest = stand_in_rows(store, place, folder)
    return [{**row, "part": "structure" if row["id"] == "mast" else "object"} for row in rows], *rest


def stand_in_boxes(jobs, folder):
    """SAM 3 finds, in the one job's place, two drums on the left (one twice), one on the right, one where no drum row
    stands, the mast, no lamp, and a crate no row names."""
    place = jobs[0]["rows"][0]["key"].split(".")[0]
    drum = [{"box": [0, 0, 20, 20]}, {"box": [1, 1, 20, 20]}, {"box": [40, 0, 60, 20]}, {"box": [150, 10, 170, 30]},
            {"box": [100, 60, 110, 70]}]
    return ({f"{place}.=drum": drum, f"{place}.=mast": [{"box": [90, 0, 110, 100]}], f"{place}.=lamp": [],
             f"{place}.~object": [{"box": [150, 50, 180, 80]}, {"box": [0, 0, 20, 20]}], f"{place}.~person": []},
            {"euros": 0.12, "wall_minutes": 10.0, "machines": [{"unit_seconds": [60.0]}]})


def row(row_id, noun, region, boxes, **more):
    """An inventory row as boxed_rows gives it, for the agreement's tests."""
    return {"id": row_id, "name": more.pop("name", noun), "noun": noun, "kind": "generate", "count": 1,
            "terrain": False, "anchor": "floor", "region": region, "boxes": boxes, "box": boxes[0] if boxes else None,
            "size": [1, 1, 1], **more}


class NoneOrMissing:
    """A wanted value read as `dict.get` reads it: the key absent or None."""


NONE_OR_MISSING = NoneOrMissing()


def wanted_key_holds(got, key, value):
    """Whether one wanted key of a dict holds: present and holding its value, or NONE_OR_MISSING read through .get."""
    if value is NONE_OR_MISSING:
        return got.get(key) is None
    return key in got and holds(got[key], value)


class Exactly:
    """A wanted value that must equal the answer whole, no key more."""

    def __init__(self, value):
        self.value = value


class Between:
    """A wanted number strictly between low and high."""

    def __init__(self, low, high):
        self.low, self.high = low, high


class Said:
    """A wanted value that is words: a non-empty string."""


SAID = Said()


class Containing(str):
    """A wanted value that is words holding these words."""


class Anything:
    """A wanted value a row does not ask after."""


ANYTHING = Anything()


class Meets:
    """A wanted value a relation on the answer holds (clear of, under, fewer than), where no one value is wanted."""

    def __init__(self, test):
        self.test = test


class All:
    """A wanted value every one of these wanted values holds."""

    def __init__(self, *wants):
        self.wants = wants


def holds(got, want):
    """Whether an answer holds what a row wants: each wanted key of a dict present and holding (NONE_OR_MISSING for a
    key read through .get), each item of a list (or a tuple's) in order and no more, an Exactly equal whole, a Between
    inside its bounds, SAID non-empty words, a Containing words holding its own, ANYTHING anything, a Meets its
    relation, an All each of its own, any other value equal."""
    if isinstance(want, Exactly):
        return got == want.value
    if isinstance(want, Between):
        return want.low < got < want.high
    if isinstance(want, Said):
        return isinstance(got, str) and bool(got.strip())
    if isinstance(want, Containing):
        return isinstance(got, str) and want in got
    if isinstance(want, Anything):
        return True
    if isinstance(want, Meets):
        return bool(want.test(got))
    if isinstance(want, All):
        return all(holds(got, each) for each in want.wants)
    if isinstance(want, dict):
        return isinstance(got, dict) and all(wanted_key_holds(got, key, value) for key, value in want.items())
    if isinstance(want, list):
        return isinstance(got, (list, tuple)) and len(got) == len(want) and all(map(holds, got, want))
    return got == want


AGREED = [  # (row, the rows Gemini read and SAM 3 boxed, SAM 3's own finds, the picture's size, kept, skipped,
    # merged exactly: kept and skipped held as `holds` reads them, None for not asked)
    ("the structure stays, a thing only one reader found is skipped",
     [row("wall", "wall", None, []), row("dome", "building", None, [], inside_place=True),
      row("rock", "rock", None, [], terrain=True), row("crate", "crate", [0, 0, 100, 100], []),
      row("chair", "chair", [0, 0, 500, 500], [[0, 0, 10, 10], [20, 0, 30, 10]]),
      row("cup", "cup", None, [], anchor="on:crate")], [{"word": "machine", "box": [50, 50, 60, 60]}], (100, 100),
     [{"id": "wall", "count": 1}, {"id": "dome", "count": 1}, {"id": "rock", "count": 1}, {"id": "chair", "count": 2}],
     [{"name": "crate", "why": reading.ONLY_GEMINI}, {"name": "cup", "why": reading.ONLY_GEMINI},
      {"name": "machine", "why": reading.ONLY_SAM}], []),
    ("a large single object only Gemini found is boxed by its region; a counted, coded, small or taken one is not",
     [row("core", "core", [200, 400, 600, 600], []),  # 8% of the picture, counted once: kept
      row("drums", "drum", [0, 0, 500, 500], [], count=3),  # counted three times: one region is no box
      row("pipes", "pipe", [0, 0, 500, 500], [], kind="code"),  # no object of its own
      row("cup", "cup", [0, 0, 100, 100], []),  # 1%: too small to stand on Gemini alone
      row("crate", "crate", [700, 700, 1000, 1000], []),  # its region is the bench's box: another's
      row("bench", "bench", None, [[700, 700, 1000, 1000]])], [], (1000, 1000),
     [{"id": "core", "box": [400.0, 200.0, 600.0, 600.0], "boxed_by": "gemini"},
      {"id": "bench", "box": [700, 700, 1000, 1000], "boxed_by": NONE_OR_MISSING}],
     [{"row": "drums"}, {"row": "pipes"}, {"row": "cup"}, {"row": "crate"}], None),
    ("one instance boxed twice on one row is one box",
     [row("chair", "chair", None, [[0, 0, 10, 10], [0, 0, 10, 11]])], [], (100, 100),
     [{"boxes": [[0, 0, 10, 10]], "count": 1}], None, None),
    ("one box held by two rows goes to the one whose region it fits",
     [row("locker", "locker", [500, 500, 600, 600], [[0, 0, 10, 10]]),
      row("chest", "chest", [0, 0, 200, 200], [[0, 0, 10, 10], [40, 40, 50, 50]])], [], (100, 100),
     [{"id": "chest", "boxes": [[0, 0, 10, 10], [40, 40, 50, 50]]}], [{"name": "locker"}], None),
    ("two rows of one thing are one row, both's instances counted once, a child on the merged one moved",
     [row("cabinet", "cabinet", None, [[0, 0, 10, 10]]),
      row("storage", "storage cabinets", None, [[0, 0, 10, 11], [60, 0, 70, 10]]),
      row("cup", "cup", None, [[62, 0, 64, 2]], anchor="on:storage")], [], (100, 100),
     [{"id": "cabinet", "count": 2}, {"id": "cup", "count": 1, "anchor": "on:cabinet"}], None,
     [{"name": "storage cabinets", "row": "storage", "into": "cabinet"}]),
]

INSIDE_ROWS = [row("hangar", "building", None, []), row("ship", "spacecraft", None, [], anchor="on:hangar"),
               row("hatch", "door", None, [], anchor="on:ship"), row("cup", "cup", None, [])]


class Refusal(str):
    """A row's outcome that is a refusal (concepts.Refused) whose words match this pattern."""


ROW_ANSWER = '{"rows": [{"id": "a", "name": "a", "noun": "a", "kind": "code", "count": 1, "size": "s", ' \
             '"anchor": "floor", "where": "w", "terrain": false, "part": "object"}]}'
CUT = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"rows": [{'}]}}],
       "usageMetadata": {"candidatesTokenCount": 2400, "thoughtsTokenCount": 63136}}
UNREAD = {"id": "a", "anchor": None, "region": None, "terrain": False, "count": 1, "size": None,
          "boxes": [[0, 0, 1, 1]]}
READ_ANSWERS = [  # (row, the reading's judging function, its arguments, the outcome as `holds` reads it, or a Refusal)
    ("a row on the schema is read, its region unread", "rows_of", (ROW_ANSWER,), [{"id": "a", "region": None}]),
    ("a count of 0", "rows_of", (ROW_ANSWER.replace('"count": 1', '"count": 0'),), Refusal("count")),
    ("a kind off the list", "rows_of", (ROW_ANSWER.replace('"kind": "code"', '"kind": "mechanic"'),), Refusal("kind")),
    ("terrain not a bool", "rows_of", (ROW_ANSWER.replace('"terrain": false', '"terrain": "no"'),), Refusal("terrain")),
    ("a part off the list", "rows_of", (ROW_ANSWER.replace('"part": "object"', '"part": "lamp"'),), Refusal("part")),
    ("an anchor on no row is a gap of its row, not a refusal", "rows_of", (ROW_ANSWER.replace('"floor"', '"on:b"'),),
     [{"anchor": None}]),
    ("no JSON", "rows_of", ("rows: none",), Refusal("no JSON")),
    ("an anchor on a row", "anchor_of", ("a", ["a", "b"]), "on:a"),
    ("a region drawn inside out", "region_of", ([10, 20, 5, 30],), None),
    ("a region", "region_of", ([10, 20, 500, 300],), [10, 20, 500, 300]),
    ("a row with no size or anchor has both gaps", "gaps", ([UNREAD],), [{"kind": "size"}, {"kind": "anchor"}]),
    ("ground the plan sizes is no gap", "gaps", ([{"id": "g", "anchor": "ground", "terrain": True, "size": None}],),
     []),
    ("metres, three", "metres_of", ([4.8, 1.9, 1.5],), [4.8, 1.9, 1.5]),
    ("metres, two", "metres_of", ([4.8, 1.9],), None),
    ("metres, one of them 0", "metres_of", ([4.8, 0, 1.5],), None),
    ("metres in words", "metres_of", ("4.8 m",), None),
    ("metres, one a bool", "metres_of", ([True, 1, 1],), None),
    ("an answer cut at its token limit is refused, its thinking named", "answer_text", (CUT,),
     Refusal("MAX_TOKENS .*thinking 63136")),
    ("a finished answer is its text", "answer_text",
     ({**CUT, "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"rows": []}'}]}}]},),
     '{"rows": []}'),
]


# --- reading fixes: a part of another row's thing merged into it, free ------------------------------------------------


SIZE = (1000, 1000)


FRIDGE = row("fridge", "fridge", [200, 810, 360, 870], [[810, 200, 870, 360]], part="object")


DOOR = row("door", "door", [210, 820, 340, 870], [[825, 220, 860, 330]], part="object")


HANDLE = row("handle", "handle", [250, 830, 260, 840], [[830, 250, 840, 260]], anchor="on:door", part="object")


CREW = row("crew", "person", [100, 500, 300, 600], [[500, 100, 600, 300]], where="sitting on a bench", part="object")


PARTED = [FRIDGE, DOOR,
          row("chair", "chair", [500, 500, 700, 700], [[500, 500, 700, 700]]),  # a person sits in it: 60% inside
          row("person", "person", [480, 500, 680, 700], [[500, 480, 700, 600]]),
          row("desk", "desk", [0, 0, 100, 100], [[0, 0, 100, 100]]),
          row("laptop", "laptop", [0, 0, 90, 90], [[10, 10, 50, 50]], anchor="on:desk")]  # stands on it: its own
SITTERS = [row("bench", "bench", None, []), row("table", "table", None, []),
           row("stool_1", "stool", None, [], name="dining stool"), row("stool_2", "stool", None, [], name="stool"),
           row("astronaut", "person", None, [], name="seated astronaut", where="sitting on bench 1"),
           row("diner", "person", None, [], name="person sitting at a table"),
           row("eater", "person", None, [], where="sitting at dining table"),
           row("visitor", "person", None, [], where="sitting on a stool"),  # two stools: which, unread
           row("pilot", "person", None, [], where="sitting on the bench", anchor="on:bench")]
ALONE = [row("floor_plates", "floor", None, []),
         row("crew", "astronaut", [400, 400, 600, 500], [[400, 400, 500, 600]], name="seated astronaut",
             where="sitting on bench", anchor="on:floor_plates", size=[0.6, 0.6, 1.4]),
         row("kid", "person", None, [], where="sitting on the floor"), row("pilot_seat", "seat", None, []),
         row("pilot", "person", None, [], where="sitting on a stool", anchor="on:pilot_seat")]
SEATED_AND_PARTED = [  # (row, the reading fix, its arguments, the outcome as `holds` reads it)
    ("only a row both readers put inside another row's thing is a part of it", reading_fixes.parts_apart,
     (PARTED, SIZE), [[{"id": "fridge"}, {"id": "chair"}, {"id": "person"}, {"id": "desk"}, {"id": "laptop"}],
                      Exactly([{"name": "door", "row": "door", "into": "fridge"}])]),
    ("a sitter on or at one seat a row is, anchored elsewhere, is anchored on it; at no seat, or two, it stays",
     reading_fixes.seats_named, (SITTERS,), Exactly({"astronaut": "on:bench", "eater": "on:stool_1"})),
    ("a sitter at a seat no row holds gets one; at a held seat, on the floor or already seated none",
     reading_fixes.seats_missing, (SITTERS,), Exactly({"diner": "chair"})),
    ("a seated astronaut on the floor gets a bench added under him, sized from him", reading_fixes.seats_added,
     (ALONE,), [[{"id": "floor_plates"}, {"id": "crew"},
                 {"id": "crew_bench", "anchor": "on:floor_plates", "size": [0.6, 0.6, 0.49],
                  "region": [500.0, 400, 600, 500], "seat_for": "crew", "added": {"reason": SAID}},
                 {"id": "kid"}, {"id": "pilot_seat"}, {"id": "pilot"}], Exactly({"crew": "on:crew_bench"})]),
]

PRICED_AND_CLEARED = [  # (row, the judging function, its arguments, the outcome as `holds` reads it)
    ("a call's cost is read from its token usage", discuss.call_euros,
     ({"usageMetadata": {"promptTokenCount": 2700, "candidatesTokenCount": 200, "thoughtsTokenCount": 1700}},),
     Between(0.02, 0.04)),
    ("sites on a plot are moved clear across it, the shed past the barn's edge", environment_plan.cleared,
     ([{"place": "barn", "x": 0.0, "y": 0.0, "footprint": [[-20, -10], [20, -10], [20, 10], [-20, 10]]},
       {"place": "shed", "x": 0.0, "y": 15.0, "footprint": [[-2, -2], [2, -2], [2, 2], [-2, 2]]}], None),
     [Exactly({"place": "barn", "x": 0.0, "y": 0.0, "footprint": [[-20, -10], [20, -10], [20, 10], [-20, 10]]}),
      {"x": 0.0, "y": 10.0 + 2.0 + environment_plan.CLEAR_M}]),
]


# --- the plan review: his edits win, a locked room moves only by his edit ---------------------------------------------


PICK = "a" * 64


PLAN_ROWS = {"shed": [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9], "count": 1,
                  "at": [{"x": 0.0, "z": -1.0, "facing": 0}]},
                 {"id": "crate", "name": "a crate", "anchor": "floor", "size": [0.5, 0.5, 0.5], "count": 2, "at": []},
                 {"id": "vice", "name": "a vice", "anchor": "bench", "size": [0.2, 0.2, 0.2], "count": 1},
                 {"id": "lamp", "name": "a wall lamp", "anchor": "wall", "size": [0.3, 0.2, 0.3], "count": 1}],
        "yard": []}


# the yard's own reading: rows on their parents, boxes that order and are their holders', sizes in metres, in words
# and none, and rows its rooms are held by
ROOM_ROWS = [{"id": "barn", "name": "a barn", "kind": "generate", "anchor": "ground", "size": [3.0, 2.0, 5.0],
              "size_words": "two storeys", "count": 1, "boxes": [[10, 10, 60, 35], [1, 1, 2, 2]]},
             {"id": "bell", "name": "a bell", "kind": "generate", "anchor": "on:barn", "size": "small", "count": 1},
             {"id": "cart", "name": "a cart", "anchor": "ground", "size": [1.5, 1.0, 1.2],
              "size_words": "two strides long", "count": 1, "boxes": []},
             {"id": "rock", "name": "a rock", "anchor": "ground", "size": None, "size_words": "waist high",
              "count": 1, "boxes": [[0, 40, 50, 50]]},
             {"id": "well", "name": "a well", "anchor": "ground", "size": "waist high", "count": 1},
             {"id": "ship", "name": "ship", "anchor": "floor", "size": [1.0, 1.0, 2.0], "count": 1, "at": [],
              "box": [70, 20, 95, 45], "view": "v1"},
             {"id": "crane", "name": "crane", "anchor": "floor", "size": [1.0, 1.0, 2.0], "count": 1, "at": []},
             {"id": "loft", "name": "loft", "anchor": "floor", "size": [1.0, 1.0, 2.0], "count": 1, "at": []}]


def plan_data(store, tmp_path, monkeypatch):
    """A holder `yard` holding `shed` (data/places/within.json, the one data file a design reads here), the plans
    kept in `tmp_path`'s own folders, and the pick's picture in the store; the data folder."""
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


THE_STORE = object()  # a held-spot row's argument standing for the plan review's own store, the shed written 4 x 10 m


def own_overlap(store, hold, other):
    """plans.laid_overlap of `hold` laid by its place's own plan in `store` and `other` by its box."""
    return plans.laid_overlap(hold, plans.own_plan(store, hold["place"]), other, None)


def gaps_laid(plan, *more):
    """plan_checks.hold_gaps of `plan` against its own grid and outline (`more`: the plan's keys replaced first)."""
    grid = plan_checks.Grid(plan)
    return plan_checks.hold_gaps({**plan, **dict(more)}, grid, grid.covered(plan_checks.outline_of(plan)))


def fitted_again(plan, shape):
    """(the shape gaps of `plan` fitted to `shape`, whether fitting the fitted plan again fits it again)."""
    fit = plan_writing.fitted(plan, shape)
    return plan_checks.shape_gaps(fit), "fitted" in plan_writing.fitted(fit, shape)["held"]


def stairs_laid_again(plan):
    """(whether `plan` has stair gaps, whether it has any laid again by plans_pass.laid_again, what that said first)."""
    laid, said = plans_pass.laid_again(plan, {"rows": []}, None)
    return bool(plan_checks.stair_gaps(plan)), bool(plan_checks.stair_gaps(laid)), said[0]


def doors_meeting(plan, held, own, fitted=()):
    """plans.doors_met on copies of `plan` and `held`: (the holds met, the gaps said, the plan's items after)."""
    plan = copy.deepcopy(plan)
    met, said = plans.doors_met(plan, copy.deepcopy(held), own, fitted)
    return met, said, plan["items"]


def fitted_then_met(plan, hold, link, own):
    """`hold` fitted to its own plan's size in `plan` (plans.hold_fitted), then met to `link`'s door as drawn and as
    fitted: (its row's item is the fitted box, met as drawn it stays, the met doors' gap within DOORS_MET, the met
    outlines overlap, the gaps said, the link's item after, the holder's hold faults)."""
    plan = copy.deepcopy(plan)
    fit, _ = plans.hold_fitted(plan, hold, plans.laid_size(hold, own[hold["place"]]))
    item_is_fit = plan["items"][0][1:5] == [fit["x"], fit["y"], fit["w"], fit["d"]]
    drawn_stays = plans.doors_met(copy.deepcopy(plan), [fit, link], own)[0][0] == fit
    met, said = plans.doors_met(plan, [fit, link], own, {hold["place"]})
    pair = record_plan.paired(own[hold["place"]], met[0], hold["place"], own[link["place"]], met[1], link["place"])[0]
    overlap = plans.laid_overlap(met[0], own[hold["place"]], met[1], own[link["place"]])
    return (item_is_fit, drawn_stays, pair["gap"] <= record_plan.DOORS_MET, overlap, said, plan["items"][1],
            record_plan.hold_faults({**plan, "holds": met}))


def door(at, to):
    """An opening of a plan: a 0.9 m door at `at` leading to `to`."""
    return {"kind": "door", "at": at, "wide": 0.9, "to": to}


TURNED_SHED = {"place": "shed", "turn": 45, "x": 0.0, "y": 0.0, "w": 9.899495, "d": 9.899495}
CORNER = {"place": "cart", "x": -1.0, "y": -1.0, "w": 2.0, "d": 2.0}  # in the 45-degree shed's box, not its outline
BAND = {"w": 20.0, "d": 20.0, "items": [["HUB", 0.0, 0.0, 10.0, 10.0, None, "item"], ["TUBE", 8.0, 8.0, 4.0, 4.0, None, "item"]],
        "rows": {"HUB": ["hub_row"], "TUBE": ["tube_row"]},
        "shapes": {"TUBE": {"shape": "polygon", "points": [[0.75, 0.0], [1.0, 0.25], [0.25, 1.0], [0.0, 0.75]]}},
        "holds": [{"place": "hub", "row": "hub_row", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0},
                  {"place": "tube", "row": "tube_row", "x": 8.0, "y": 8.0, "w": 4.0, "d": 4.0}]}
FLAT_ROOM = {"w": 4.78, "d": 4.78, "outline": [[0, 0], [4.78, 0], [4.78, 4.78], [0, 4.78]], "rows": {"BED 1": ["bed"]},
             "items": [["BED 1", 1.0, 1.0, 2.0, 1.0, "E", "item"]], "doors": [["E", 2.39, 0.9, "DOOR"]],
             "leads": {"E": {"to": "stairwell"}}}
FLAT_SHAPE = {"w": 6.0, "d": 5.0, "from": "the kit's flat"}
STREET = {"w": 10.0, "d": 6.0, "outline": [[0, 0], [10.0, 0], [10.0, 6.0], [0, 6.0]], "rows": {},
          "items": [["CAR 1", 0.0, 0.0, 4.0, 2.0, "E", "item"]], "doors": [["N", 2.0, 3.0, "GATE"]],
          "leads": {"N": {"to": "square"}}}
CORE = {"w": 2.8, "d": 5.0, "doors": [], "items": [], "rows": {}, "levels": [], "outline": [],
        "walls": [{"from": [0, 0], "to": [2.8, 0], "thick": 0.2}, {"from": [2.8, 0], "to": [2.8, 5.0], "thick": 0.2},
                  {"from": [2.8, 5.0], "to": [0, 5.0], "thick": 0.2}, {"from": [0, 5.0], "to": [0, 0], "thick": 0.2}],
        "stairs": [{"kind": "stair", "points": [[0.2, 2.0], [1.4, 2.0], [1.4, 3.0], [0.2, 3.0]], "from": 0.0,
                    "to": 1.5, "angle": 270.0, "steps": 9}]}
SQUARE_DOORS = {"flat": {"w": 6.0, "d": 5.0, "openings": [door([5.925, 1.344], "stairwell")]},
                "stairwell": {"w": 7.4, "d": 4.0, "openings": [door([0.0, 0.88], "flat")]}}
SQUARE_HELD = [{"place": "flat", "row": "left_building", "x": 0.0, "y": 16.0, "w": 6.0, "d": 5.0},
               {"place": "stairwell", "row": None, "x": 10.0, "y": 24.0, "w": 7.4, "d": 4.0}]
LANTERNED = {"items": [["LANTERN 1", 6.5, 17.5, 1.0, 1.0, None, "item"]], "rows": {}}
TUBES = [{"place": "stairwell", "instance": f"stairwell#{number}", "row": "core", "x": 10.0 * number, "y": 0.0,
          "w": 7.4, "d": 4.0} for number in (1, 2)]
AIRLOCK_DOORS = {"lock": {"w": 4.0, "d": 4.0, "openings": [door([2.0, 0.08], "link")]},
                 "link": {"w": 2.0, "d": 6.0, "openings": [door([1.0, 6.0], "lock")]}}
LINKED = {"items": [["MODULE 1", 0.0, 8.0, 10.0, 10.0, None, "item"], ["LINK 1", 6.0, 3.0, 5.656854, 5.656854, None, "item"]],
          "rows": {"MODULE 1": ["module"], "LINK 1": ["link"]}}
LOCK = {"place": "lock", "row": "module", "x": 0.0, "y": 8.0, "w": 10.0, "d": 10.0, "turn": 45}
LINK = {"place": "link", "row": "link", "x": 6.0, "y": 3.0, "w": 5.656854, "d": 5.656854, "turn": 45}
HELD_SPOTS = [  # (row, the held-spot judging function, its arguments, the outcome as `holds` reads it, or a Refusal)
    # a hold turned 90 degrees takes its plan's size turned (#72: the base's hangar, drawn wide, its plan long)
    ("a quarter-turned hold lays the shed's own 4 x 10 m turned", plans.laid_own_size,
     (THE_STORE, {"place": "shed", "turn": 90, "x": 0.0, "y": 0.0, "w": 1.0, "d": 1.0}), [10.0, 4.0]),
    ("a 45-degree hold lays its own box", plans.laid_own_size, (THE_STORE, TURNED_SHED), [9.899495, 9.899495]),
    # a place held several times keeps each instance its own (the base's tubes); an instance names its place, a hold
    # turns from 0 up to 360 degrees, a lead names a place, an instance or one door of several by its spot
    ("an instance names its place", plans.checked_instance, ({"instance": "Tube#3", "turn": 90, "leads": {"hub": "lab"}},
                                                             "tube"),
     Exactly({"instance": "tube#3", "turn": 90, "leads": {"hub": "lab"}})),
    ("a lead names one door by its spot", plans.checked_instance,
     ({"turn": 332.33, "leads": {"tube@15.8335,2.3405": "tube#5"}}, "hub"),
     Exactly({"turn": 332.33, "leads": {"tube@15.8335,2.3405": "tube#5"}})),
    ("an instance of another place", plans.checked_instance, ({"instance": "hub#1"}, "tube"),
     Refusal("no instance of tube")),
    ("a turn of 360", plans.checked_instance, ({"turn": 360}, "tube"), Refusal("from 0 up to 360")),
    ("a lead at no spot", plans.checked_instance, ({"leads": {"tube@north": "hub"}}, "tube"),
     Refusal("no place, instance or door")),
    # the shed turned 45 degrees in its 9.9 m box leaves the box's corners empty: a spot in one overlaps its box only
    ("a spot in the turned shed's empty corner", own_overlap, (THE_STORE, TURNED_SHED, CORNER), False),
    ("the same spot against its box alone", plans.laid_overlap, (TURNED_SHED, None, CORNER, None), True),
    # the free checks judge two holds' tiling by their drawn outlines too (the item of the hold's row on its box)
    ("a tube drawn off the hub's corner", gaps_laid, (BAND,), []),
    ("the tube drawn as its box", gaps_laid, (BAND, ("shapes", {})), [{"words": "hub and tube overlap"}]),
    # a held place off its creator's shape by more than SHAPE_SLACK on an axis is fitted to it, its things at their own
    # size, and one not fitted is a gap (#72: the flat written 4.78 x 4.78 m for its 6 x 5 m inside)
    ("the flat off its shape", plan_checks.shape_gaps, ({**FLAT_ROOM, "held": FLAT_SHAPE},), [{"kind": "shape"}]),
    ("the flat fitted to its shape", plan_writing.fitted, (FLAT_ROOM, FLAT_SHAPE),
     {"w": 6.0, "d": 5.0, "held": {"fitted": {"scale": [1.2552, 1.046]}},
      "items": [["BED 1", 1.51, 1.069, 2.0, 1.0, "E", "item"]], "doors": [["E", 2.5, 0.9, "DOOR"]]}),
    ("the fitted flat: no shape gap, fitted again as it is", fitted_again, (FLAT_ROOM, FLAT_SHAPE), [[], False]),
    # one whose proportions run the other way is turned a quarter first (the street drawn east to west for its 8 x
    # 36 m strip north to south): its things, facings, doors and leads with it
    ("the street turned a quarter", plan_writing.fitted, (STREET, {"w": 8.0, "d": 36.0}),
     {"held": {"fitted": {"turned": True}}, "w": 8.0, "d": 36.0, "items": [["CAR 1", 5.667, 5.2, 2.0, 4.0, "S", "item"]],
      "doors": [["E", 7.2, 3.0, "GATE"]], "leads": Exactly({"E": {"to": "square"}})}),
    # a kept writing is laid again by the writer's free steps: its flights built from their rises (#87)
    ("a kept core's flights built", stairs_laid_again, (CORE,), [True, False, Containing("1 flights built")]),
    # two held places whose doors to each other open apart meet: the one on the holder's own floor moved by the gap and
    # off its sibling's box (the Square's stairwell opened its door to the flat 10.4 m from the flat's, 2026-11-05);
    # one held in a row's item stays where it is drawn, and two such are left for the gate to name
    ("the stairwell on the Square's floor meets the flat's door", doors_meeting, (LANTERNED, SQUARE_HELD, SQUARE_DOORS),
     [[Exactly(SQUARE_HELD[0]), {"x": 6.0, "y": 16.464}], [{"item": "stairwell"}, {"item": "LANTERN 1"}],
      [["LANTERN 1", 5.0, 17.5, 1.0, 1.0, None, "item"]]]),
    ("both held in a row's item: left for the gate", doors_meeting,
     (LANTERNED, [SQUARE_HELD[0], {**SQUARE_HELD[1], "row": "core"}], SQUARE_DOORS), [ANYTHING, [], ANYTHING]),
    ("two instances of one place: left", doors_meeting,
     (LANTERNED, TUBES, {hold["instance"]: SQUARE_DOORS["stairwell"] for hold in TUBES}), [Exactly(TUBES), [], ANYTHING]),
    # a hold fitted to its plan's size takes its row's drawn item with it, and, no longer as drawn, moves so its door
    # meets its turned link's end, backed off along its door's wall, the link's own item left where it is drawn (the
    # base's airlock: fitted from its 18.5 m module item to its 7 m plan, item left, its door 4 m off tube#3's, 2026-11-05)
    ("the airlock fitted to its plan meets tube#3's door", fitted_then_met, (LINKED, LOCK, LINK, AIRLOCK_DOORS),
     [True, True, True, False, [{"item": "lock"}], ["LINK 1", 6.0, 3.0, 5.656854, 5.656854, None, "item"], []]),
]


# --- plan writing and its free checks: each failure a named gap -------------------------------------------------------


ANSWER = {
    "outline": [[0, 0], [4, 0], [4, 3], [0, 3]],
    "walls": [{"from": [0, 0], "to": [4, 0], "thick": 0.2, "tall": 2.5}, {"from": [4, 0], "to": [4, 3], "thick": 0.2},
              {"from": [4, 3], "to": [0, 3], "thick": 0.2}, {"from": [0, 3], "to": [0, 0], "thick": 0.2},
              {"from": "nowhere"}],
    "openings": [{"kind": "door", "at": [2.0, 3.0], "wide": 0.9, "angle": 0, "swing": "left", "head": 2.1,
                  "to": "yard"}],
    "levels": [{"name": "floor", "height": 0, "points": [[0, 0], [4, 0], [4, 3], [0, 3]]}],
    "roofs": [{"kind": "pitched", "points": [[0, 0], [4, 0], [4, 3], [0, 3]], "eave": 2.5, "top": 3.4,
               "openings": [{"points": [[1, 1], [2, 1], [2, 2], [1, 2]]}, {"points": [[1, 1]]}]}],
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


def writing_stand_ins(monkeypatch):
    """The plan writer's paid calls stood in: each writing 0.04 EUR, its top-down drawing a white picture at 0.12 EUR
    (its wordings kept in `ask.drawn`), each ask answering ANSWER at UNITS a metre (its bodies kept); the asked list and
    the ask."""
    asked, drawn = [], []
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)

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


def clearing(cleared_for):
    def clear(store, places, euros, node):
        cleared_for.append((node, places, euros))
        return compute.reading_clearance(store, places, euros, node=node)
    return clear


WALLED = {"w": 6.0, "d": 4.0, "doors": [["S", 3.0, 1.0, "DOOR"]], "people": [[1.0, 1.0]],
          "items": [["WALL OF CRATES 1", 0.0, 2.0, 6.0, 0.6, None, "item"]], "rows": {"WALL OF CRATES 1": ["crate"]},
          "holds": [{"place": "a", "x": 0, "y": 0, "w": 3, "d": 2}, {"place": "b", "x": 2, "y": 0, "w": 3, "d": 2},
                    {"place": "c", "x": 5, "y": 3, "w": 3, "d": 3}]}
CRATE_ROW = {"rows": [{"id": "crate", "anchor": "floor", "count": 1}]}
# the stairwell's flights (#87): 1.5 m over a 1 m run, one over the next in one lane, one through the east wall;
# the writer builds each from its rise, lays them inside the core's walls apart and a landing where they turn
STAIR_CORE = {"w": 2.8, "d": 5.0, "doors": [], "items": [], "rows": {}, "levels": [],
              "walls": [{"from": [0, 0], "to": [2.8, 0], "thick": 0.2}, {"from": [2.8, 0], "to": [2.8, 5.0], "thick": 0.2},
                        {"from": [2.8, 5.0], "to": [0, 5.0], "thick": 0.2}, {"from": [0, 5.0], "to": [0, 0], "thick": 0.2}],
              "stairs": [{"kind": "stair", "points": [[0.2, 2.0], [1.4, 2.0], [1.4, 3.0], [0.2, 3.0]], "from": 0.0,
                          "to": 1.5, "angle": 270.0, "steps": 9},
                         {"kind": "stair", "points": [[0.2, 1.5], [1.4, 1.5], [1.4, 2.5], [0.2, 2.5]], "from": 3.0,
                          "to": 1.5, "angle": 270.0, "steps": 9},
                         {"kind": "stair", "points": [[2.2, 3.0], [3.2, 3.0], [3.2, 4.0], [2.2, 4.0]], "from": 3.0,
                          "to": 4.5, "angle": 270.0, "steps": 9}]}


BOX_2D = {"outline": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
          "items": [{"row": "bench", "box_2d": [100, 200, 160, 400]}],
          "places": [{"place": "nook", "box_2d": [500, 500, 700, 800]}]}
BENCH_METRES = {"rows": [{"id": "bench", "size": [2.0, 0.6, 0.9]}]}
HELD_BOX = {"w": 2.0, "d": 6.0, "doors": [["S", 1.0, 0.9, "DOOR"], ["E", 3.0, 0.9, "DOOR"]]}
ROWS_METRES = Exactly({"metres a unit": [0.01, 0.01], "by": "its rows' metres"})
MEASURED = [  # (row, the footprint measure, its arguments: answer, skeleton, inventory, held; found, skeleton, how)
    ("a footprint answered as box_2d is measured from its box", plan_writing.measured,
     (BOX_2D, {"w": 1.0, "d": 1.0}, BENCH_METRES, False),
     [{"items": [{"x": 3.0, "y": 1.3, "wide": 2.0, "deep": 0.6}], "places": [{"x": 5.0, "y": 5.0, "w": 3.0, "d": 2.0}]},
      {"w": 10, "d": 10}, ROWS_METRES]),
    # a held place keeps its own size: its rows' metres both ways and its drawn outline, never its holder's box shape
    # (#72: the Square's 2.145 x 6.609 m strip stretched the flat 2.3x across); its doors keep their share of the wall
    ("a held place keeps its rows' metres and its doors their share of the wall", plan_writing.measured,
     (BOX_2D, HELD_BOX, BENCH_METRES, True),
     [{"items": [{"wide": 2.0}]}, {"w": 10, "d": 10, "doors": [["S", 5.0, 0.9, "DOOR"], ["E", 5.0, 0.9, "DOOR"]]},
      ROWS_METRES]),
    ("a held place no row tells is measured by its box's floor, the same both ways", plan_writing.measured,
     (BOX_2D, HELD_BOX, {"rows": []}, True),
     [{}, {"w": 3.464, "d": 3.464}, {"metres a unit": [0.00346, 0.00346]}]),
]


CONCEPT_ROWS = {"picture": [1000, 1000], "rows": [  # a hub in the middle, a dome left, a hangar behind, a tube hub-dome
    {"id": "hub", "count": 1, "boxes": [[400, 400, 600, 600]]},
    {"id": "dome", "count": 1, "boxes": [[100, 420, 250, 580]]},
    {"id": "hangar", "count": 1, "boxes": [[350, 50, 650, 200]]},
    {"id": "tube", "count": 1, "boxes": [[250, 480, 400, 520]]}]}
AS_DRAWN = {"w": 40.0, "d": 40.0, "doors": [], "people": [[30.0, 35.0]],
            "items": [["HUB 1", 20.0, 20.0, 10.0, 10.0, None, "item"], ["DOME 1", 2.0, 21.0, 8.0, 8.0, None, "item"],
                      ["HANGAR 1", 15.0, 0.0, 20.0, 10.0, None, "item"],
                      ["TUBE 1", 10.0, 24.0, 10.0, 2.0, None, "item"]],
            "rows": {"HUB 1": ["hub"], "DOME 1": ["dome"], "HANGAR 1": ["hangar"], "TUBE 1": ["tube"]}}
DESK_ROWS = {"picture": [1000, 1000], "rows": [  # a pad in the middle, a desk left, a rack right, about one depth
    {"id": "pad", "count": 1, "boxes": [[400, 600, 600, 700]]},
    {"id": "desk", "count": 1, "boxes": [[50, 600, 150, 700]]},
    {"id": "rack", "count": 1, "boxes": [[850, 600, 950, 700]]},
    {"id": "crate", "count": 6, "size": [0.8, 0.8, 0.8], "boxes": [[0, 0, 10, 10]]}]}
DESK_LAID = [["PAD 1", 14.0, 10.0, 4.0, 4.0, None, "item"], ["DESK 1", 1.0, 10.0, 2.0, 1.0, "S", "item"],
             ["RACK 1", 28.0, 10.0, 2.0, 1.0, None, "item"], ["CRATE 1", 1.0, 1.0, 4.0, 1.0, None, "item"]]
DESKS = {"w": 32.0, "d": 20.0, "doors": [], "people": [[16.0, 18.0]], "items": DESK_LAID,
         "rows": {"PAD 1": ["pad"], "DESK 1": ["desk"], "RACK 1": ["rack"], "CRATE 1": ["crate"]},
         "shapes": {"CRATE 1": {"count": 6}, "DESK 1": {"seen": ["toward"]}}}
DINER_ROWS = {"rows": [{"id": "crate", "count": 1}, {"id": "diner", "noun": "person", "count": 1},
                       {"id": "distant_flag", "count": 1}, {"id": "stage", "count": 1}]}
DINER = {"w": 6.0, "d": 4.0, "doors": [], "people": [[4.0, 3.0, None, "diner"]],
         "items": [["CRATE 1", 1.0, 1.0, 1.0, 1.0, None, "item"], ["DINER 1", 1.2, 1.2, 0.5, 0.5, None, "item"],
                   ["DISTANT FLAG 1", 9.0, 1.0, 1.0, 1.0, None, "item"]],
         "rows": {"CRATE 1": ["crate"], "DINER 1": ["diner"], "DISTANT FLAG 1": ["distant_flag"]}}
GAP_WORDS = [  # (row, a written plan, its inventory, the gap kinds read or None for all, the gaps' words: a list is
    # exactly them, a set is among them)
    ("laid as the concept, seen from the south", AS_DRAWN, CONCEPT_ROWS, {"arrangement", "joined"}, []),
    ("the dome put right of the hub and the tube off by itself", {**AS_DRAWN, "items": [
        AS_DRAWN["items"][0], ["DOME 1", 31.0, 21.0, 8.0, 8.0, None, "item"], AS_DRAWN["items"][2],
        ["TUBE 1", 2.0, 34.0, 10.0, 2.0, None, "item"]]}, CONCEPT_ROWS, {"arrangement", "joined"},
     {"dome is left of hub in the concept, right of it on the plan",
      "hub is joined by a tube in the concept, by none on the plan"}),
    ("a run of 6 crates is all 6, each row where drawn and facing as drawn", DESKS, DESK_ROWS, None, []),
    ("the pad off to the side, the desk turned away", {**DESKS, "items": [
        ["PAD 1", 22.0, 10.0, 4.0, 4.0, None, "item"], ["DESK 1", 1.0, 10.0, 2.0, 1.0, "N", "item"], *DESK_LAID[2:]]},
     DESK_ROWS, None, {"pad stands in the middle of the concept (50% across), on the right of the plan (81% across)",
                       "desk 1 faces toward in the concept, away on the plan"}),
    ("6 crates boxed round half the place", {**DESKS, "items": [*DESK_LAID[:3], ["CRATE 1", 1.0, 1.0, 12.0, 8.0, None,
                                                                                  "item"]]},
     DESK_ROWS, None, {"crate 1 boxes 6 things drawn apart as one (12.0 x 8.0 m), not one run"}),
    ("a person on its spot and a thing seen far off are no gaps; a row not laid is", DINER, DINER_ROWS, None,
     ["stage: 1 in the concept, 0 on the plan"]),
    ("a row marked beyond the place is no gap", {**DINER, "beyond": ["stage"]}, DINER_ROWS, None, []),
    ("a wall of crates walls the standing spot in; inside places overlapping or sticking out", WALLED, CRATE_ROW, None,
     {"the standing spot (north-west) cannot be reached on foot", "a and b overlap", "c sticks out of the place"}),
    ("a cable on the floor is walked over", {**WALLED, "shapes": {"WALL OF CRATES 1": {"shape": "rect", "tall": 0.05}}},
     CRATE_ROW, {"reach"}, []),
    ("a way round the crates: every door and spot reached",
     {**WALLED, "items": [["WALL OF CRATES 1", 0.0, 2.0, 4.0, 0.6, None, "item"]]}, CRATE_ROW, {"reach"}, []),
    ("a flight too steep, two overlapping, one past its walls", STAIR_CORE, {"rows": []}, {"stairs"},
     {"stair 1 rises 1.5 m over a 1.00 m run, 56 degrees (steeper than 42)", "stair 1 and stair 2 overlap, under 2 m apart",
      "stair 3 lies past its walls (south-east)"}),
]


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


SHIP = {"what": "the ship's floor plan", "places": ["bridge", "hold"], "length": 10.0, "wide": 4.0, "base": 1.0,
        "tall": 3.0, "outline": [[0, 0], [2, 4], [2, 10], [-2, 10], [-2, 4]],
        "rooms": {"bridge": [[-1, 2], [1, 2], [1, 5], [-1, 5]], "hold": [[-2, 5], [2, 5], [2, 10], [-2, 10]]}}


def ship_laid(nose):
    """A plan holding the bridge and the hold on its ship's 4 x 2 m box, the ship's nose read as `nose`."""
    return {"items": [["SHIP 1", 18.0, 9.0, 4.0, 2.0, nose, "item"]], "rows": {"SHIP 1": ["ship"]}, "shapes": {},
            "holds": [{"place": "bridge", "row": "ship", "x": 0, "y": 0, "w": 1, "d": 1},
                      {"place": "hold", "row": "ship", "x": 1, "y": 0, "w": 1, "d": 1}]}


SHIP_ON_HIS_PLAN = {  # its own 10 x 4 m, nose east, the same middle; its rooms where his plan draws them
    "items": [["SHIP 1", 15.0, 8.0, 10.0, 4.0, "E", "item"]], "rows": {"SHIP 1": ["ship"]},
    "shapes": {"SHIP 1": {"shape": "polygon", "points": [[1.0, 0.5], [0.6, 1.0], [0.0, 1.0], [0.0, 0.0], [0.6, 0.0]],
                          "tall": 3.0, "base": 1.0, "planned": "the ship's floor plan"}},
    "holds": [{"place": "bridge", "row": "ship", "x": 20.0, "y": 9.0, "w": 3.0, "d": 2.0},
              {"place": "hold", "row": "ship", "x": 15.0, "y": 8.0, "w": 5.0, "d": 4.0}]}
BARE = {**plans.base_plan("no_such_place"), "w": 3.0, "d": 2.0}  # a scene added in the app: no doors of its own
OPENINGS = [{"kind": "door", "at": [11.5, 7.0], "wide": 0.9, "sill": 0.0, "head": 2.1, "to": "airlock"},
            {"kind": "gate", "at": [13.05, 5.6], "wide": 1.2, "sill": 0.0, "head": 2.4, "to": "outside"},
            {"kind": "door", "at": [0.0, 1.0], "wide": 0.9, "sill": 0.0, "head": 2.1, "to": "sealed"}]
HELD_DOORS = {**BARE, "doors": [["S", 1.5, 0.9, "door 0.9 x 2.1 m"], ["E", 0.6, 1.2, "gate 1.2 x 2.4 m"]], "leads": {
    "S": {"to": "hangar", "why": "the hangar plan's door at [11.5, 7.0] is in this place's S wall"},
    "E": {"to": "outside", "why": "the hangar plan's gate at [13.05, 5.6] is in this place's E wall"}}}
OWN_DOORS = {**BARE, "doors": [["N", 1.0, 0.9, "DOOR"]], "leads": {"N": {"to": "sealed", "why": "filed"}}}
TREE_ROW = {"rows": [{"id": "tree", "count": 4, "size": [1.0, 1.0, 5.0]}]}
TREES = {"w": 12.0, "d": 12.0, "doors": [], "people": [], "items": [["TREE 1", 1.0, 1.0, 10.0, 10.0, None, "item"]],
         "rows": {"TREE 1": ["tree"]}, "shapes": {"TREE 1": {"shape": "circle", "count": 4}}}
TREES_SPLIT = {**TREES, "items": [["TREE 1", 1.0, 1.0, 1.0, 1.0, None, "item"],
                                  ["TREE 2", 10.0, 1.0, 1.0, 1.0, None, "item"],
                                  ["TREE 3", 10.0, 10.0, 1.0, 1.0, None, "item"],
                                  ["TREE 4", 1.0, 10.0, 1.0, 1.0, None, "item"]],
               "rows": {f"TREE {number}": ["tree"] for number in range(1, 5)},
               "shapes": {f"TREE {number}": {"shape": "circle"} for number in range(1, 5)}}
THE_PLAN_ITSELF = object()  # a wanted answer that is the very plan the fix was given, kept as it is


def one_laid(row_id, words):
    """stand_in_plan with one of the row's three things laid at plan (3.0, 2.1) and its inventory: two more boxed at
    (3.5, 2.3), crossing the laid one, and (6.3, 2.3), its words `words`."""
    plan, name = stand_in_plan(), row_id.upper()
    plan["items"].append([f"{name} 1", 3.0, 2.1, 0.6, 0.4, None, "item"])
    plan["rows"][f"{name} 1"] = [row_id]
    return plan, {"picture": [1000, 1000], "rows": [*ROWS, {
        "id": row_id, "count": 3, "size": [0.6, 0.4, 0.2], "size_words": words,
        "boxes": [[300, 200, 360, 230], [320, 200, 380, 230], [600, 200, 660, 230]]}]}


def placed_where_shown(plan, inventory):
    """plan_fixes.placed_missing as the free fixes call it: through the plan's own projection of the concept."""
    return plan_fixes.placed_missing(plan, inventory, plan_fixes.projector(plan, inventory))


def placed_said(row_id):
    """What placed_where_shown says it placed: the row's two missing things and the stand-in's missing barrel."""
    return ["barrel: 1 more placed where the concept shows them", f"{row_id}: 2 more placed where the concept shows them"]


def missing_placed(name, piled):
    """The plan's items and shapes once the row's two missing things are placed: the crossing one at (3.2, 2.1), on the
    laid one at its 0.2 m when `piled`, the other at (6.0, 2.1) on the floor; the stand-in's missing barrel beside."""
    return {"items": [*stand_in_plan()["items"], [f"{name} 1", 3.0, 2.1, 0.6, 0.4, None, "item"],
                      ["BARREL 2", 1.5, 6.5, 1.0, 1.0, None, "item"], [f"{name} 2", 3.2, 2.1, 0.6, 0.4, None, "item"],
                      [f"{name} 3", 6.0, 2.1, 0.6, 0.4, None, "item"]],
            "shapes": Exactly({"DESK 1": {"shape": "rect", "seen": ["toward"]}, "BARREL 2": {"shape": "rect"},
                               f"{name} 2": {"shape": "rect", **({"base": piled} if piled else {})},
                               f"{name} 3": {"shape": "rect"}})}


CUBE = [1.0, 1.0, 1.0]
FOOT_ROWS = {"picture": [1000, 1000], "rows": [  # sandbags boxed at the concept's foot, marked beyond with no item
    {"id": "plates", "anchor": "ground", "count": 1, "boxes": [[0, 500, 1000, 1000]]},
    {"id": "barrel", "count": 2, "size": CUBE, "boxes": [[150, 400, 250, 500], [750, 400, 850, 500]]},
    {"id": "pallet", "anchor": "on:plates", "count": 1, "size": CUBE, "boxes": [[450, 700, 550, 800]]},
    {"id": "desk", "count": 1, "size": CUBE, "boxes": [[750, 200, 850, 300]]},
    {"id": "sandbags", "anchor": "ground", "count": 1, "size": CUBE, "boxes": [[450, 900, 550, 1000]]}]}
FOOT_ITEMS = [["BARREL 1", 1.5, 4.5, 1.0, 1.0, None, "item"], ["BARREL 2", 7.5, 4.5, 1.0, 1.0, None, "item"],
              ["PALLET 1", 4.5, 7.5, 1.0, 1.0, None, "item"], ["DESK 1", 7.5, 2.5, 1.0, 1.0, None, "item"]]
AT_THE_FOOT = {"w": 10.0, "d": 10.0, "doors": [], "people": [], "items": FOOT_ITEMS, "structure": ["plates"],
               "beyond": ["sandbags"], "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in FOOT_ITEMS}}
NO_ROWS = {"rows": []}
SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]
SPOTS_BEYOND = {"w": 10.0, "d": 10.0, "outline": SQUARE, "items": [],  # lab, 2026-11-02: its people on spots inside
                "people": [[2.0, 3.0, 0.0, "person"], [7.0, 6.0, 0.0, "person"], [4.0, 12.0, 0.0, "walker"],
                           [5.0, 5.0, 0.0, "walker"]], "beyond": ["person", "walker", "skyline"]}
MAN_ROW = {"rows": [{"id": "person_man", "noun": "man", "name": "man walking up stairs", "count": 1}]}
UNSTOOD = {"w": 10.0, "d": 10.0, "outline": SQUARE, "people": [[1.5, 3.0]],  # stairwell's writing of 2026-10-21
           "items": [["PERSON MAN 1", 3.0, 3.0, 0.6, 0.6, None, "item"]], "rows": {"PERSON MAN 1": ["person_man"]},
           "beyond": ["person_man", "skyline"], "fixes": []}
STOOD = {**UNSTOOD, "items": [], "rows": {}, "people": [[3.3, 3.3, 0.0, "person_man"], [1.5, 3.0]]}
WORKERS = {"rows": [{"id": "worker_blue", "noun": "worker", "name": "worker in blue", "count": 4,
                     "size": [0.5, 0.3, 1.8]}, {"id": "crate", "noun": "crate", "name": "crate", "count": 1}]}
HANGAR = {"w": 32.0, "d": 64.0, "people": [[40.0, 10.0]], "items": [["CRATE 1", 6.0, 14.0, 6.0, 6.0, None, "item"]],
          "rows": {"CRATE 1": ["crate"]}, "fixes": []}
SPREAD = {**HANGAR, "people": [  # its four workers on the free floor inside its 32 x 64 m, clear of the crate
    [40.0, 10.0], [8.24, 13.84, 0.0, "worker_blue"], [23.76, 24.24, 0.0, "worker_blue"],
    [23.76, 47.92, 0.0, "worker_blue"], [8.24, 39.76, 0.0, "worker_blue"]]}
GARAGE = {"w": 12.0, "d": 12.0, "outline": [[0, 0], [12, 0], [12, 12], [0, 12]], "fixes": [], "rows": {},
          "items": [["PIPE 1", -5.0, 1.5, 10.0, 0.1, None, "item"], ["FACADE 1", -3.01, 11.8, 14.0, 0.6, None, "item"],
                    ["GLASS TUNNEL 1", -4.0, 5.0, 4.0, 2.0, None, "item"], ["CRATE 1", 4.0, 4.0, 1.0, 1.0, None, "item"]],
          "people": [[7.0, 14.3]], "frame": {"anchor": {"plan": [60.0, 3.0], "place": [0, 0, 0]}}}
GARAGE_INSIDE = {key: value for key, value in GARAGE.items() if key != "frame"} | {
    "items": [["PIPE 1", 0.0, 1.5, 10.0, 0.1, None, "item"], ["FACADE 1", 0.0, 11.4, 12.0, 0.6, None, "item"],
              ["GLASS TUNNEL 1", -4.0, 5.0, 4.0, 2.0, None, "item"], ["CRATE 1", 4.0, 4.0, 1.0, 1.0, None, "item"]],
    "people": [[6.975, 11.775]]}
STOOL_ROWS = {"picture": [1000, 1000], "rows": [row for row in ROWS if row["id"] != "barrel"] + [
    {"id": "stool", "count": 1, "size": [0.5, 0.5, 0.5]}]}  # no box: no free fix places it
STOOD_TURNED_MOVED = ["worker: stood as 1 person spot where the concept shows them",
                      "desk 1: turned to face toward as in the concept", "crate 1: moved 0.8 m out of desk 1"]
STOOL_ASKED = {"euros": 0.07, "notes": ["stool: 1 in the concept, 0 on the plan"]}
unsettled_unparted = functools.partial(plans_pass.unsettled, parts=False)


def placed_gaps(plan, inventory, structure):
    """The rows plan_checks.checked lists as placed gaps on `plan`, `structure` the place's own shell rows."""
    return [gap["row"] for gap in plan_checks.checked(plan, inventory, structure) if gap["kind"] == "placed"]


def correcting(store, place, plan, left, ask):
    """A stand-in Correct: the shed's lays the stool its gaps name, the hut's changes nothing; its call sends the
    gaps' words as its notes at 0.07 euros."""
    laid = [["STOOL 1", 3.0, 3.0, 0.5, 0.5, None, "item"]] if place == "shed" else []
    return ({**plan, "items": plan["items"] + laid, "rows": {**plan["rows"], "STOOL 1": ["stool"]}} if laid else plan,
            {"euros": 0.07, "notes": [gap["words"] for gap in left]})


STAND_IN_ROWS = {"picture": [1000, 1000], "rows": ROWS}


def gap_kinds(plan, inventory):
    """The kinds of the gaps plan_checks.checked lists on `plan`."""
    return [gap["kind"] for gap in plan_checks.checked(plan, inventory)]


def laid_boxes(plan):
    """Each item's laid box [x, y, w, d] by its name."""
    return {item[0]: item[1:5] for item in plan["items"]}


def kept_apart_of(plan, inventory):
    """(the items, the fixes said) plan_fixes.kept_apart leaves on a copy of `plan`."""
    plan = copy.deepcopy(plan)
    said = plan_fixes.kept_apart(plan, inventory)
    return plan["items"], said


def stacked_left(plan, inventory):
    """The stacked gaps left open on `plan`, each saying why."""
    return [gap for gap in plan_fixes.why_left(plan_fixes.open_gaps(plan, inventory)) if gap["kind"] == "stacked"]


def flight_gaps_left(plan, inventory):
    """The things left on a flight as made, each saying why."""
    return plan_fixes.why_left(plan_fixes.flight_gaps(plan, inventory))


NO_DROPPED = Meets(lambda plan: "dropped" not in plan)
# 2026-11-04 audit: the doorways are the design's door rows (habitat's 2.2 m hatches drawn 0.237 m wide, galley's W
# door drawn on its S wall), and a wall row re-counted is a gap like a floor row (lab's pipes 10 to 6)
DOORED = {"w": 10.0, "d": 10.0, "items": [["PIPE 1", 0.0, 2.0, 0.2, 3.0, None, "item"]], "rows": {"PIPE 1": ["pipe"]},
          "doors": [["N", 5.0, 1.0, "DOOR N 1.0 x 2.2 m"], ["W", 3.0, 0.9, "HATCH W 0.9 x 2.0 m"]],
          "leads": {"N": {"to": "yard"}, "W": {"to": "sealed"}},
          "openings": [{"kind": "door", "at": [5.0, 0.0], "wide": 0.3, "sill": 0.0, "head": 2.2, "to": "yard"},
                       {"kind": "door", "at": [5.0, 10.0], "wide": 1.4, "sill": 0.0, "head": 2.0, "to": "sealed"},
                       {"kind": "window", "at": [10.0, 5.0], "wide": 1.0, "sill": 1.0, "head": 2.0, "to": None}]}
# the walkway's east wall (2026-11-05): its galley door shut, its quarters door leading there by its own lead
WALKWAY = {"w": 2.0, "d": 12.0,
           "doors": [["E", 3.0, 0.9, "DOOR to the galley"], ["E", 9.0, 0.9, "DOOR to the quarters"]],
           "leads": {"E": {"to": "sealed"}, "E:9": {"to": "quarters"}},
           "openings": [{"kind": "door", "at": [2.0, 9.2], "wide": 0.9, "sill": 0.0, "to": "sealed"},
                        {"kind": "door", "at": [2.0, 3.1], "wide": 0.9, "sill": 0.0, "to": "sealed"}]}
PIPE_WALL = {"id": "pipe", "anchor": "wall", "count": 3, "size": [0.2, 3.0, 0.2]}
# settle@airlock, checkout 67: a run of sandbags through its east wall, one into its ramp's stairs, one nudged into
# the empty suit hung on its back wall
BAGS_ROW = {"id": "bags", "anchor": "ground", "count": 1, "size": [0.6, 0.5, 0.2]}
RUNS = {"w": 10.0, "d": 10.0, "items": [["BAGS 1", 1.0, 2.0, 7.0, 0.5, None, "item"],
                                        ["BAGS 2", 1.0, 8.8, 3.0, 0.5, None, "item"],
                                        ["BAGS 3", 6.5, 6.0, 3.0, 0.5, None, "item"],
                                        ["PIPE 1", 5.9, 1.0, 0.2, 3.0, None, "item"]],
        "rows": {"BAGS 1": ["bags"], "BAGS 2": ["bags"], "BAGS 3": ["bags"], "PIPE 1": ["pipe"]},
        "shapes": {**{f"BAGS {number}": {"shape": "rect", "tall": 0.2, "base": -0.2, "count": count}
                      for number, count in ((1, 7), (2, 3), (3, 3))},
                   "PIPE 1": {"shape": "rect", "tall": 0.2, "count": 2}},
        "walls": [{"from": [6.0, 0.0], "to": [6.0, 5.0], "thick": 0.2}, {"from": [0.0, 9.0], "to": [5.0, 9.0],
                                                                          "thick": 0.2}],
        "stairs": [{"kind": "ramp", "points": [[7.0, 5.0], [8.0, 5.0], [8.0, 7.0], [7.0, 7.0]]}]}
RUN_ROWS = {"rows": [BAGS_ROW, {**PIPE_WALL, "anchor": "on:wall"}]}
DOUBLED = {"w": 10.0, "d": 10.0, "items": [["BAGS 1", 1.0, 1.0, 3.0, 0.5, None, "item"],
                                           ["BAGS 2", 1.2, 1.1, 0.6, 0.4, None, "item"],
                                           ["BAGS 3", 1.2, 1.1, 0.6, 0.4, None, "item"],
                                           ["BAGS 4", 3.9, 1.4, 0.6, 0.4, None, "item"],
                                           ["CRATE 1", 2.0, 1.0, 0.6, 0.4, None, "item"]],
           "rows": {"BAGS 1": ["bags"], "BAGS 2": ["bags"], "BAGS 3": ["bags"], "BAGS 4": ["bags"],
                    "CRATE 1": ["crate"]},
           "shapes": {"BAGS 1": {"shape": "rect", "tall": 0.2, "base": -0.2, "count": 5},
                      "BAGS 2": {"shape": "rect", "tall": 0.2, "base": -0.2},
                      "BAGS 3": {"shape": "rect", "tall": 0.2, "base": 0.0},
                      "BAGS 4": {"shape": "rect", "tall": 0.2, "base": -0.2},
                      "CRATE 1": {"shape": "rect", "tall": 0.5, "base": -0.2}}}
CROWDED = {"w": 10.0, "d": 10.0, "items": [["CRATE 1", 2.0, 4.0, 2.0, 2.0, None, "item"],
                                           ["BOX 1", 3.6, 4.5, 0.8, 0.5, None, "item"],
                                           ["SUIT 1", 4.5, 4.4, 0.5, 0.7, "W", "item"]],
           "rows": {"CRATE 1": ["crate"], "BOX 1": ["box"], "SUIT 1": ["suit"]},
           "shapes": {"SUIT 1": {"shape": "rect", "tall": 1.8, "base": 0.1}}}
CROWDED_ROWS = {"rows": [{"id": "crate"}, {"id": "box"}, {"id": "suit", "anchor": "on:wall"}]}
PANELLED = {**CROWDED, "items": [*CROWDED["items"], ["PANEL 1", 0.0, 0.0, 10.0, 10.0, None, "item"]],
            "rows": {**CROWDED["rows"], "PANEL 1": ["wall_panel"]},
            "shapes": {**CROWDED["shapes"], "PANEL 1": {"shape": "rect", "tall": 2.8, "base": 0.0}}}
# settle@flat and settle@engineroom, checkout 68: a plan fixed before piled() asked the row's words kept flat's second
# stove 0.9 m up on its first, in its fridge, and the engine room's pipe 1 ran into its corner pipes
KITCHEN = {"w": 6.0, "d": 5.0, "items": [["FRIDGE 1", 4.95, 1.95, 0.6, 0.6, "W", "item"],
                                         ["STOVE 1", 4.94, 2.59, 0.54, 1.0, "W", "item"],
                                         ["STOVE 2", 4.58, 2.13, 0.8, 0.6, None, "item"],
                                         ["BAGS 1", 1.0, 1.0, 1.0, 0.5, None, "item"],
                                         ["BAGS 2", 1.2, 1.1, 1.0, 0.5, None, "item"],
                                         ["RAIL 1", 0.5, 3.0, 1.0, 1.0, None, "item"],
                                         ["RAIL 2", 0.6, 3.1, 1.0, 1.0, None, "item"],
                                         ["PANEL 1", 0.0, 0.0, 6.0, 5.0, None, "item"],
                                         ["PIPE 1", 1.0, 0.0, 4.0, 0.3, None, "item"],
                                         ["PIPE 2", 0.8, 0.0, 0.6, 0.3, None, "item"],
                                         ["PIPE 3", 4.6, 0.0, 0.6, 0.3, None, "item"],
                                         ["STRING 1", 0.0, 4.0, 6.0, 0.2, None, "item"],
                                         ["STRING 2", 0.0, 4.1, 6.0, 0.2, None, "item"],
                                         ["FRAME 1", 3.0, 4.8, 0.5, 0.1, None, "item"],
                                         ["FRAME 2", 3.1, 4.8, 0.5, 0.1, None, "item"]],
           "rows": {"FRIDGE 1": ["fridge"], "STOVE 1": ["stove"], "STOVE 2": ["stove"], "BAGS 1": ["sandbags"],
                    "BAGS 2": ["sandbags"], "RAIL 1": ["railing"], "RAIL 2": ["railing"],
                    "PANEL 1": ["wall_panel"], "PIPE 1": ["pipe"], "PIPE 2": ["pipe"], "PIPE 3": ["pipe"],
                    "STRING 1": ["lantern_string"], "STRING 2": ["lantern_string"], "FRAME 1": ["frame"],
                    "FRAME 2": ["frame"]},
           "shapes": {"FRIDGE 1": {"shape": "rect", "tall": 1.8, "base": 0.0},
                      "STOVE 1": {"shape": "rect", "tall": 0.9, "base": 0.0},
                      "STOVE 2": {"shape": "rect", "tall": 0.9, "base": 0.9},
                      "BAGS 1": {"shape": "rect", "tall": 0.3, "base": 0.0},
                      "BAGS 2": {"shape": "rect", "tall": 0.3, "base": 0.3},
                      "RAIL 1": {"shape": "rect", "tall": 1.0, "base": 0.0},
                      "RAIL 2": {"shape": "rect", "tall": 1.0, "base": 1.0},
                      "PANEL 1": {"shape": "rect", "tall": 2.8, "base": 0.0},
                      "PIPE 1": {"shape": "rect", "tall": 0.2, "base": 2.5},
                      "PIPE 2": {"shape": "rect", "tall": 0.2, "base": 2.5},
                      "PIPE 3": {"shape": "rect", "tall": 0.2, "base": 1.0},
                      "STRING 1": {"shape": "rect", "tall": 0.5, "base": 6.0},
                      "STRING 2": {"shape": "rect", "tall": 0.5, "base": 6.5},
                      "FRAME 1": {"shape": "rect", "tall": 0.6, "base": 0.2},
                      "FRAME 2": {"shape": "rect", "tall": 0.6, "base": 1.2}}}
KITCHEN_ROWS = {"rows": [{"id": "fridge"}, {"id": "stove"}, {"id": "sandbags", "where": "a pile by the door"},
                         {"id": "grating", "anchor": "ground"}, {"id": "railing", "anchor": "on:grating"},
                         {"id": "hull", "anchor": "ground", "part": "wall"},
                         {"id": "wall_panel", "anchor": "on:hull", "part": "wall"},
                         {"id": "pipe", "anchor": "on:wall_panel"},
                         {"id": "lantern_string", "anchor": "on:grating"},
                         {"id": "frame", "anchor": "on:wall_panel"}]}
KITCHEN_WRITTEN = {**KITCHEN, "fixes": []}  # a writing fixed before kept_apart: the pass fixes it again
KITCHEN_PIPED = {**KITCHEN_WRITTEN, "shapes": {**KITCHEN["shapes"], "PIPE 1": {**KITCHEN["shapes"]["PIPE 1"],
                                                                              "count": 8}}}
BOXED_IN = {**KITCHEN, "items": [*KITCHEN["items"], ["CRATE 9", 0.0, 0.0, 6.0, 5.0, None, "item"]],  # the whole floor
            "rows": {**KITCHEN["rows"], "CRATE 9": ["crate"]},  # taken: its second stove alone piled, its rail stood
            "shapes": {**KITCHEN["shapes"], "RAIL 2": {**KITCHEN["shapes"]["RAIL 2"], "base": 0.0}}}
BOXED_ROWS = {"rows": [*KITCHEN_ROWS["rows"], {"id": "crate"}]}


def symmetric_fit():
    """settle@engineroom, checkout 68: its grating, doors and windows each laid round the room's middle, so the fit
    sent every concept box to it and its four missing railings were laid on one spot: (the plan, its concept's rows)."""
    plan, rows = {"w": 10.0, "d": 10.0, "items": [], "rows": {}}, []
    for number, (row, near, far) in enumerate((("grate", [2.0, 5.0], [8.0, 5.0]), ("door", [5.0, 1.0], [5.0, 9.0]),
                                               ("lamp", [3.0, 3.0], [7.0, 7.0]))):
        rows.append({"id": row, "count": 2, "boxes": [[100 + 300 * number, 400, 200 + 300 * number, 500 + 100 * side]
                                                      for side in (0, 1)]})
        for side, (x, y) in enumerate((near, far)):
            plan["items"].append([f"{row.upper()} {side + 1}", x - 0.5, y - 0.5, 1.0, 1.0, None, "item"])
            plan["rows"][f"{row.upper()} {side + 1}"] = [row]
    return plan, {"picture": [1000, 1000], "rows": rows}


SYMMETRIC = symmetric_fit()
# settle@campgrounds, checkout 68: habitat dome 2 drawn a 6.37 m circle, made 10 m across (its read size), its ramp
# laid 0.62 m off the circle and so inside the dome
DOMED = {"w": 24.0, "d": 24.0, "items": [["DOME 1", 3.0, 3.0, 6.0, 6.0, None, "item"],
                                         ["LANDER 1", 14.0, 2.0, 6.0, 6.0, None, "item"],
                                         ["TOWER 1", 2.0, 16.0, 4.0, 4.0, None, "item"]],
         "rows": {"DOME 1": ["dome"], "LANDER 1": ["lander"], "TOWER 1": ["tower"]},
         "shapes": {"DOME 1": {"shape": "circle", "tall": 6.0}, "LANDER 1": {"shape": "circle", "tall": 8.0},
                    "TOWER 1": {"shape": "rect", "tall": 30.0}},
         "stairs": [{"kind": "ramp", "points": [[5.5, 9.6], [6.5, 9.6], [6.5, 11.6], [5.5, 11.6]], "from": 0.0,
                     "to": 0.5, "angle": 90.0},
                    {"kind": "ramp", "points": [[16.5, 7.0], [17.5, 7.0], [17.5, 9.0], [16.5, 9.0]], "from": 0.0,
                     "to": 2.0, "angle": 270.0},
                    {"kind": "stair", "points": [[7.0, 17.0], [8.0, 17.0], [8.0, 19.0], [7.0, 19.0]], "from": 0.0,
                     "to": 3.0, "angle": 0.0}]}
MADE_ROWS = {"rows": [{"id": "dome", "anchor": "ground", "size": [10.0, 10.0, 6.0]},
                      {"id": "lander", "anchor": "ground", "size": [8.0, 8.0, 8.0]},
                      {"id": "tower", "anchor": "ground", "size": [30.0, 30.0, 30.0]}]}
# settle@garage, checkout 68: split_runs laid seven 10 m pipes along x, items_inside clamped three into one corner at
# [0, 0] and the holders stood them over one another on the north wall
GARAGE_PIPES = {"w": 12.0, "d": 12.0, "outline": [[0.0, 0.0], [12.0, 0.0], [12.0, 12.0], [0.0, 12.0]],
                "walls": [{"from": [0.0, 0.0], "to": [12.0, 0.0], "thick": 0.3},
                          {"from": [12.0, 0.0], "to": [12.0, 12.0], "thick": 0.3},
                          {"from": [12.0, 12.0], "to": [0.0, 12.0], "thick": 0.3},
                          {"from": [0.0, 12.0], "to": [0.0, 0.0], "thick": 0.3}],
                "items": [["PIPE 1", 0.0, 0.0, 10.0, 0.1, None, "item"], ["PIPE 2", 0.0, 0.0, 10.0, 0.1, None, "item"],
                          ["PIPE 3", 0.0, 0.0, 10.0, 0.1, None, "item"], ["PIPE 4", 1.0, 11.9, 10.0, 0.1, None, "item"],
                          ["PIPE 5", 0.5, 0.0, 10.0, 0.1, None, "item"], ["PIPE 6", 0.0, 0.0, 10.0, 0.1, None, "item"],
                          ["DUCT 1", 1.0, 0.0, 8.0, 0.2, None, "item"], ["CRANE 1", 1.0, 0.5, 10.0, 1.0, None, "item"],
                          ["CRANE 2", 1.0, 3.0, 10.0, 1.0, None, "item"]],
                "rows": {**{f"PIPE {number}": ["pipe"] for number in range(1, 7)}, "DUCT 1": ["pipe"],
                         "CRANE 1": ["crane"], "CRANE 2": ["crane"]},
                "shapes": {**{f"PIPE {number}": {"shape": "rect", "tall": 0.1, "base": 0.0} for number in range(1, 7)},
                           "PIPE 6": {"shape": "rect", "tall": 0.1, "base": 3.0},
                           "DUCT 1": {"shape": "rect", "tall": 0.2, "base": 0.0, "count": 2},
                           "CRANE 1": {"shape": "rect", "tall": 1.0, "base": 6.0},
                           "CRANE 2": {"shape": "rect", "tall": 1.0, "base": 6.0}}}
GARAGE_PIPE_ROWS = {"rows": [{"id": "pipe", "anchor": "wall", "where": "walls", "size": [10.0, 0.1, 0.1], "count": 8},
                             {"id": "crane", "anchor": "wall", "where": "top, spanning left to right",
                              "size": [10.0, 1.0, 1.0], "count": 2}]}
# settle@greenhouse, checkout 68: its upper floor at 3 m stood over its dome's 2.8 m eave, its reading's stairs row laid
# two stairs objects on the shell's three flights, and planter beds made 2.5 m stood on the flights' feet
EAVED = {"w": 10.0, "d": 10.0, "walls": [{"from": [0.0, 0.0], "to": [10.0, 0.0], "tall": 2.8}],
         "levels": [{"name": "lower floor", "height": 0.0, "points": [[3, 3], [7, 3], [7, 7], [3, 7]]},
                    {"name": "upper floor", "height": 3.0, "points": [[0, 0], [10, 0], [10, 10], [0, 10]]}],
         "roofs": [{"kind": "dome", "points": [[0, 0], [10, 0], [10, 10], [0, 10]], "eave": 2.8, "top": 6.2}]}


def eaved(low, roof):
    """EAVED with its one level at `low` and its roof's own values `roof`."""
    return {**EAVED, "levels": [{**EAVED["levels"][1], "height": low}], "roofs": [{**EAVED["roofs"][0], **roof}]}


FLIGHTS = [{"kind": "stair", "points": [[0.2, 2.0], [1.2, 2.0], [1.2, 4.0], [0.2, 4.0]], "from": 0.0, "to": 3.0,
            "angle": 270.0, "steps": 8}]
STAIRS_WALLED = {"stairs": FLIGHTS, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 6.0, 6.0, None, "item"],
                                              ["STAIRCASE 1", 4.0, 0.0, 1.0, 3.0, None, "item"]],
                 "rows": {"ON THE WALLS AND CEILING": ["outer_wall", "stairs"], "STAIRCASE 1": ["staircase"]},
                 "shapes": {}}
STAIR_ROWS = {"rows": [{"id": "outer_wall", "noun": "wall"}, {"id": "stairs", "noun": "stairs"},
                       {"id": "staircase", "noun": "stairs"}, {"id": "stair_railing", "noun": "railing",
                                                               "anchor": "on:staircase"}]}
BEDS = {"w": 6.0, "d": 6.0, "stairs": FLIGHTS,
        "levels": [{"name": "floor", "height": 0.0, "points": [[0, 0], [6, 0], [6, 4.6], [0, 4.6]]},
                   {"name": "gallery", "height": 3.0, "points": [[0, 4.6], [6, 4.6], [6, 6], [0, 6]]}],
        "items": [["CHAIR 1", 1.3, 4.3, 0.3, 0.3, None, "item"], ["BED 1", 2.5, 2.5, 0.5, 0.5, None, "item"],
                  ["CART 1", 0.5, 3.8, 0.4, 0.4, None, "item"], ["HALL 1", 1.25, 1.0, 0.5, 0.5, None, "item"]],
        "rows": {"CHAIR 1": ["chair"], "BED 1": ["bed"], "CART 1": ["cart"], "HALL 1": ["hall"]},
        "shapes": {name: {"shape": "rect", "tall": 0.5, "base": 0.0} for name in ("CHAIR 1", "BED 1", "CART 1",
                                                                                "HALL 1")}}
BED_ROWS = {"rows": [{"id": "chair", "size": [1.0, 1.0, 0.9]}, {"id": "bed", "size": [5.0, 5.0, 0.5]},
                     {"id": "cart", "size": [0.6, 0.6, 0.8]}, {"id": "hall", "size": [9.0, 9.0, 9.0]}]}
BEDS_CLEAR = {**BEDS, "items": [["CHAIR 1", 1.625, 3.875, 0.3, 0.3, None, "item"], *BEDS["items"][1:]]}  # its chair
# moved off the stairs. greenhouse's live plan (2026-11-09): eleven planter beds made up to 2.5 m on a lower floor that
# holds six clear of the stairs
BEDS_ROWED = {**BEDS_CLEAR, "items": [*BEDS_CLEAR["items"], ["BED 2", 3.6, 0.1, 0.5, 0.5, None, "item"]],
              "rows": {**BEDS["rows"], "BED 2": ["bed"]}}
POTTED_ROWS = {"rows": [*BED_ROWS["rows"], {"id": "pot", "anchor": "on:bed", "size": [0.3, 0.3, 0.3]}]}


def potted_beds(others):
    """greenhouse's live plan (2026-11-09): its plants 2 stood on planter bed 2, taken off its flights' feet, so 0.5 m
    up over bare floor. BEDS_CLEAR with POT 1 on BED 1, and with `others` BED 2 with POT 2 on it: neither row's last."""
    potted = copy.deepcopy(BEDS_CLEAR)
    potted["items"].append(["POT 1", 2.6, 2.6, 0.3, 0.3, None, "item"])
    if others:
        potted["items"] += [["BED 2", 3.6, 0.1, 0.5, 0.5, None, "item"], ["POT 2", 3.7, 0.2, 0.3, 0.3, None, "item"]]
    potted["rows"].update({"BED 2": ["bed"], "POT 1": ["pot"], "POT 2": ["pot"]})
    potted["shapes"].update({name: {"shape": "rect", "tall": 0.3, "base": 0.5} for name in ("POT 1", "POT 2")})
    return potted


POTTED_ONE = potted_beds(False)
# settle@airlock, env1 checkout 71: sandbags made 0.6 x 0.4 m, 6 on a 0.4 x 1.23 m box, parted by the assembly into
# one another and its locker's suit; its ramp, laid by the holders up to its locker floor's edge, through a wall
SACKS = {"w": 6.0, "d": 4.0, "walls": [{"from": [0.0, 0.0], "to": [6.0, 0.0], "thick": 0.1}],
         "items": [["BAGS 1", 0.5, 0.5, 1.2, 0.5, None, "item"], ["BAGS 2", 3.5, 3.0, 1.3, 0.5, None, "item"],
                   ["BAGS 3", 0.2, 2.6, 0.6, 1.2, None, "item"], ["SUIT 1", 2.0, 0.3, 0.5, 0.5, "S", "item"],
                   ["BAGS 4", 3.0, 4.3, 1.2, 0.8, None, "item"]],
         "rows": {"BAGS 1": ["bags"], "BAGS 2": ["bags"], "BAGS 3": ["bags"], "SUIT 1": ["suit"],
                  "BAGS 4": ["bags"]},
         "shapes": {"BAGS 1": {"shape": "rect", "tall": 0.2, "base": 0.0, "count": 4},
                    "BAGS 2": {"shape": "rect", "tall": 0.2, "base": 0.0, "count": 2},
                    "BAGS 3": {"shape": "rect", "tall": 0.2, "base": 0.0, "count": 9},
                    "SUIT 1": {"shape": "rect", "tall": 1.8, "base": 0.0},
                    "BAGS 4": {"shape": "rect", "tall": 0.2, "base": 0.0, "count": 3}}}
SACK_ROWS = {"rows": [{"id": "bags", "anchor": "ground", "count": 18, "size": [0.6, 0.4, 0.2]},
                      {"id": "suit", "anchor": "on:back_wall", "count": 1, "size": [0.6, 0.4, 1.8]}]}


def bags_three_cut(plan):
    """Whether BAGS 3's run of nine is cut to fewer the 4 m room holds end to end inside it, as long as they are as
    made, the cut said in `dropped`."""
    kept, box = plan["shapes"]["BAGS 3"]["count"], laid_boxes(plan)["BAGS 3"]
    return kept < 9 and box[2:] == [0.4, round(0.6 * kept, 3)] and 0.0 <= box[1] and box[1] + box[3] <= 4.0 and \
        plan["dropped"] == [{"item": "bags", "why": f"{9 - kept} fewer of it laid, its runs as long as their free "
                                                    f"floor holds as made: {9 + kept} laid", "laid": 9 + kept}]


# settle@storage, 2026-11-10: six 2 m cable bundles "round the ceiling edges" on one 2.68 m box, laid 0.45 m apart
# in one another
SQUARE_HALL = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]
HUNG_HALL = {"w": 6.0, "d": 4.0, "outline": SQUARE_HALL,
             "walls": [{"from": start, "to": end, "thick": 0.2}
                       for start, end in zip(SQUARE_HALL, SQUARE_HALL[1:] + SQUARE_HALL[:1])],
             "items": [["CABLES 1", 1.0, 0.1, 2.6, 0.1, None, "item"], ["LAMPS 1", 2.5, 1.5, 0.5, 0.5, None, "item"]],
             "rows": {"CABLES 1": ["cables"], "LAMPS 1": ["lamps"]},
             "shapes": {"CABLES 1": {"shape": "rect", "tall": 0.1, "base": 3.0, "count": 6},
                        "LAMPS 1": {"shape": "rect", "tall": 0.2, "base": 2.8, "count": 3}}}
HUNG_ROWS = {"rows": [{"id": "cables", "anchor": "ceiling", "count": 6, "size": [2.0, 0.1, 0.1]},
                      {"id": "lamps", "anchor": "ceiling", "count": 3, "size": [0.4, 0.4, 0.2]}]}
RAMP_ROW = {"id": "ramp", "name": "metal ramp", "noun": "ramp", "anchor": "ground", "count": 1, "size": [1.2, 2.0, 0.2]}


def loft_ramp(walled_off):
    """A 6 m room with a loft at 0.5 m and a ramp laid toward it; `walled_off` a wall between the ramp and the loft."""
    return {"w": 6.0, "d": 6.0, "walls": [{"from": [0.0, 0.0], "to": [6.0, 0.0], "thick": 0.1}] + (
                [{"from": [3.0, 0.0], "to": [3.0, 6.0], "thick": 0.1}] if walled_off else []),
            "levels": [{"name": "loft", "height": 0.5, "points": [[4, 0], [6, 0], [6, 6], [4, 6]]}],
            "items": [["RAMP 1", 1.0, 2.5, 1.0, 1.0, None, "item"]], "rows": {"RAMP 1": ["ramp"]},
            "shapes": {"RAMP 1": {"shape": "rect", "tall": 0.3, "base": 0.0}}}


LOFT_BAGGED = loft_ramp(False)  # a run clear of the ramp as drawn, in it where the holders lay it
LOFT_BAGGED["items"].append(["BAGS 1", 2.2, 2.8, 1.2, 0.4, None, "item"])
LOFT_BAGGED["rows"]["BAGS 1"] = ["bags"]
LOFT_BAGGED["shapes"]["BAGS 1"] = {"shape": "rect", "tall": 0.2, "base": 0.0, "count": 2}
# hub, 2026-11-11: 16 monitor screens on a 1.75 m console top, 19 on a 2.73 m bank, laid in one another
MONITOR_ROWS = {"rows": [{"id": "desk", "anchor": "floor", "count": 1, "size": [2.0, 0.8, 0.8]},
                         {"id": "monitor", "anchor": "floor", "count": 5, "size": [0.5, 0.1, 0.4]}]}


def console_of(count):
    """A 2 m desk with `count` monitors drawn 0.4 m apart over it, 0.8 m up: on its top."""
    console = {"w": 6.0, "d": 4.0, "items": [["DESK 1", 1.0, 1.0, 2.0, 0.8, "S", "item"]],
               "rows": {"DESK 1": ["desk"]}, "shapes": {"DESK 1": {"shape": "rect", "tall": 0.8, "base": 0.0}}}
    for number in range(1, count + 1):
        console["items"].append([f"MONITOR {number}", 0.6 + 0.4 * number, 1.3, 0.5, 0.1, "S", "item"])
        console["rows"][f"MONITOR {number}"] = ["monitor"]
        console["shapes"][f"MONITOR {number}"] = {"shape": "rect", "tall": 0.4, "base": 0.8}
    return console


FIXED = [  # (row, the plan writer's fix, its arguments, the answer as `holds` reads it, the plan given it after
    # or None, and optionally what the same fix answers when given that plan again)
    ("a thing the creator planned is laid from his plan: its own size and nose round the same middle, its rooms "
     "where his plan draws them", plan_writing.creator_laid, (ship_laid("E"),), [{"bridge", "hold"}, []],
     Exactly(SHIP_ON_HIS_PLAN)),
    ("a planned thing whose nose was not read is laid nose east, said", plan_writing.creator_laid, (ship_laid(None),),
     [{"bridge", "hold"}, [{"words": "the way ship 1's nose points was not read: laid nose E"}]], None),
    # a scene added in the app gets a door for each of its holder's openings in its walls: one into it leads back to
    # the holder, one in a shared outer wall where that opening leads; the plan stage reads its height off its words
    ("a scene added in the app takes its doors from its holder's openings into it", plan_writing.held_doors,
     (BARE, "airlock", "hangar", [10.0, 5.0, 3.0, 2.0], OPENINGS), Exactly(HELD_DOORS), None),
    ("the plan stage cuts those doors, each its height read off its words", record_plan.doors_of,
     (HELD_DOORS, {"rows": []}), [{"side": "south", "leads": "hangar", "tall": 2.1, "cut": True},
                                  {"side": "east", "leads": "outside", "tall": 2.4, "cut": True}], None),
    ("a place with doors of its own keeps them", plan_writing.held_doors,
     (OWN_DOORS, "airlock", "hangar", [10.0, 5.0, 3.0, 2.0], OPENINGS), THE_PLAN_ITSELF, None),
    # 2026-10-30: placed_missing laid each missing copy at full size with no neighbour check (airlock's sandbags in each
    # other by 5 to 25 cm); 2026-11-06: the engine room's railings piled 1 to 4 m over one another the same way. Only a
    # row whose words say its things pile piles; railings laid alike all stand on the floor
    ("a missing thing crossing one of its row whose words pile is piled on it, the other on the floor",
     placed_where_shown, one_laid("sack", "a knee high pile"), placed_said("sack"), missing_placed("SACK", 0.2)),
    ("missing things of a row whose words do not pile stand on the floor", placed_where_shown,
     one_laid("railing", "waist high"), placed_said("railing"), missing_placed("RAILING", None)),
    ("a box of four things drawn apart as one is a run gap", plan_checks.run_gaps, (TREES, TREE_ROW),
     [{"kind": "arrangement", "item": "TREE 1"}], None),
    ("a box of things drawn apart is split round its spread, each its own size and shape", plan_fixes.split_runs,
     (TREES, TREE_ROW, None), Exactly(["tree 1: split into its 4 things"]), Exactly(TREES_SPLIT)),
    ("split, it is no run gap", plan_checks.run_gaps, (TREES_SPLIT, TREE_ROW), [], None),
    # 2026-10-26: the airlock's sandbags at its picture's foot were marked beyond and had no plan item, its rows of
    # several things and its rows on the floor plates fitting no projection; the check lists them all the same
    ("a row at the concept's foot marked beyond is a placed gap all the same", placed_gaps,
     (AT_THE_FOOT, FOOT_ROWS, ["plates"]), ["sandbags"], None),
    ("brought in from beyond, it is placed where its box's foot projects, at y = 10", plan_fixes.fixed,
     (AT_THE_FOOT, FOOT_ROWS), [{"beyond": [], "items": [*FOOT_ITEMS, ["SANDBAGS 1", 4.5, 9.5, 1.0, 1.0, None, "item"]]},
                                ["sandbags: at the concept's foot, so on this place's ground, not beyond it",
                                 "sandbags: 1 more placed where the concept shows them"]], None),
    # lab, 2026-11-02: a row marked beyond whose person spots all stand inside is in; one seen past a window stays
    ("people on spots inside the outline are in the place, not beyond it", plans_pass.brought_inside, (SPOTS_BEYOND,),
     [{"beyond": ["walker", "skyline"]}, ["person: stands on person spots inside this place, so in it, not beyond it"]],
     None),
    ("plans keep fixes people marked beyond inside again, free", unsettled_unparted, (SPOTS_BEYOND, NO_ROWS), True, None),
    # stairwell, 2026-11-02: a writing older than stood_people, its man on the stairs on no spot and marked beyond
    ("a people row a writing never stood is unstood", plans_pass.unstood, (UNSTOOD, MAN_ROW), ["person_man"], None),
    ("plans keep fixes an unstood writing again, free", unsettled_unparted, (UNSTOOD, MAN_ROW), True, None),
    ("an unstood row is stood where its item lies, the item no furniture", plans_pass.stood_again, (UNSTOOD, MAN_ROW),
     [Exactly(STOOD), ["person man: stood as 1 person spot where the concept shows them"]], None),
    ("stood, it is brought in from beyond", plans_pass.brought_inside, (STOOD,),
     [{"beyond": ["skyline"]}, ["person man: stands on person spots inside this place, so in it, not beyond it"]], None),
    ("a writing whose people all stand is left as it is", plans_pass.stood_again, (STOOD, MAN_ROW),
     [Exactly(STOOD), []], None),
    # the hangar's eight workers stood on none, four dealt view spots outside it (2026-11-04): no box projects and no
    # thing is laid, so its count spreads over the free floor inside the outline, clear of the crate
    ("a row with no box that projects and no thing laid is spread over the free floor", plans_pass.stood_again,
     (HANGAR, WORKERS), [Exactly(SPREAD), ["worker blue: no box of it projects, so its 4 people spread over the free "
                                          "floor"]], None),
    ("spread, it is no unstood row", plans_pass.unstood, (SPREAD, WORKERS), [], None),
    # 2026-11-05: the garage's 10 m pipes 5 m past its wall, the galley's spot at x 5.72 in 4.64 m, the Square's frame
    # anchor at [60, 3] in its 29 m: an item moved the least way, a run longer than the side clipped first, a person
    # spot to the nearest free floor with its footprint inside, a frame in another plan's metres dropped
    ("plans keep fixes what a plan lays past its outline again, free", unsettled_unparted, (GARAGE, NO_ROWS), True,
     None),
    ("what the plan lays past its own outline is brought inside it", plan_fixes.kept_inside, (GARAGE, NO_ROWS),
     ["its frame's anchor [60.0, 3.0] lay outside its 12 x 12 m plan, set in another plan's metres: dropped, the plan "
      "stands unturned", "pipe 1: moved 5.00 m inside the plan's outline", "facade 1: clipped from 14 x 0.6 m to 12 x "
      "0.6 m and moved 3.04 m inside the plan's outline", "a standing spot: its spot [7.0, 14.3] moved 2.53 m inside "
      "the plan's outline"], Exactly(GARAGE_INSIDE)),
    ("brought inside, nothing is brought in again", plan_fixes.kept_inside, (GARAGE_INSIDE, NO_ROWS), [], None),
    # a Correct is kept only when it leaves fewer gaps, and what is left says why (stand-in Corrects: `correcting`)
    ("a Correct that lays the missing stool is kept, the stool's gap its notes", functools.partial(
        plan_fixes.settled, None, "shed"), (stand_in_plan(), STOOL_ROWS, None),
     [{"gaps": [], "fixes": [*STOOD_TURNED_MOVED, "the prompt model corrected 1 gaps", STOOD_TURNED_MOVED[0]]},
      [STOOL_ASKED]], None),
    ("a Correct that changes nothing is not kept, the stool's gap left saying why", functools.partial(
        plan_fixes.settled, None, "hut"), (stand_in_plan(), STOOL_ROWS, None),
     [{"gaps": [{"words": f"stool: 1 in the concept, 0 on the plan: {plan_fixes.WHY['placed']}"}],
       "fixes": STOOD_TURNED_MOVED}, [STOOL_ASKED]], None),
    # the free fixes on the stand-in plan: people stood (a person no furniture), the missing barrel where its box
    # projects, the desk facing the viewer as in the concept; no gap left
    ("the stand-in plan has placed, people, overlap and arrangement gaps", gap_kinds, (stand_in_plan(), STAND_IN_ROWS),
     Meets(lambda kinds: {"placed", "people", "overlap", "arrangement"} <= set(kinds)), None),
    ("the free fixes stand people, place the missing, face the desk: four fixes and no gap left", plan_fixes.fixed,
     (stand_in_plan(), STAND_IN_ROWS), [All(
         {"people": Meets(lambda people: people[:2] == [[5.0, 3.0, 0.0, "worker"], [9.5, 9.5]])},
         Meets(lambda plan: "WORKER 1" not in laid_boxes(plan)),
         Meets(lambda plan: sorted(box[:2] for name, box in laid_boxes(plan).items() if name.startswith("BARREL"))
               == [[1.5, 6.5], [7.5, 6.5]]),
         Meets(lambda plan: next(item for item in plan["items"] if item[0] == "DESK 1")[5] == "S"),
         Meets(lambda plan: plan_checks.checked(plan, STAND_IN_ROWS) == [])), Meets(lambda fixes: len(fixes) == 4)],
     None),
    ("a plan's doorways are its door rows: as wide as said, on the side said, leading where its lead does",
     plan_fixes.doors_kept, (DOORED, {}), [SAID, SAID],
     {"openings": [{"at": [5.0, 0.0], "wide": 1.0, "to": "yard"}, {"at": [0.0, 3.0], "wide": 0.9, "to": "sealed"},
                   {"at": [10.0, 5.0], "wide": 1.0, "to": None}]}, []),
    ("two door rows on one wall each take the doorway nearest where they stand along it, each by its own lead",
     plan_fixes.doors_kept, (WALKWAY, {}), ANYTHING,
     {"openings": [{"at": [2.0, 9.2], "to": "quarters"}, {"at": [2.0, 3.1], "to": "sealed"}]}),
    ("a wall row re-counted is a gap like a floor row", plan_checks.count_gaps, (DOORED, {"rows": [PIPE_WALL]}, set()),
     [{"words": "pipe: 3 in the concept, 1 on the plan"}], None),
    # a run a wall or stair crosses keeps its longer side, its count cut with its length; one a wall runs along moves
    # off it; a run on a wall is left there. 2026-11-09: the cut said nowhere, the next pass laid the five cut bags
    # back; the cut is said with what it lays, so the row's count is no gap
    ("runs are kept clear of the walls and stairs, the cut said with what it lays", plan_fixes.runs_kept_clear,
     (RUNS, RUN_ROWS), [SAID, SAID, SAID], All(
         Meets(lambda plan: [(item[1:5], plan["shapes"][item[0]]["count"]) for item in plan["items"]] == [
             ([1.0, 2.0, 4.85, 0.5], 5), ([1.0, 9.15, 3.0, 0.5], 3), ([8.05, 6.0, 1.45, 0.5], 1),
             ([5.9, 1.0, 0.2, 3.0], 2)]),
         {"dropped": Exactly([{"item": "bags", "why": "4 fewer of it laid, its runs cut clear of the walls and "
                                                      "stairs: 9 laid", "laid": 9}])},
         Meets(lambda plan: plan_checks.count_gaps(plan, {"rows": [{**BAGS_ROW, "count": 13}]}, set()) == [])), []),
    ("a single bag laid in its own row's run at its base is taken off; one piled on it, one touching its end and "
     "another row's left", plan_fixes.run_doubles_dropped, (DOUBLED, {"rows": [BAGS_ROW, {"id": "crate"}]}),
     Exactly(["bags: bags 2 taken off, 1 laid again in its own row's run, which lays its pieces there: 7 laid"]),
     {"items": Meets(lambda items: [item[0] for item in items] == ["BAGS 1", "BAGS 3", "BAGS 4", "CRATE 1"]),
      "dropped": Meets(lambda dropped: dropped[0]["laid"] == 7)}, []),
    ("a nudge lands in no suit hung on the wall", plan_fixes.nudged, (CROWDED, CROWDED_ROWS), ANYTHING,
     {"items": Meets(lambda items: items[1][1:3] == [3.6, 3.45])}),
    ("the room-sized wall panel blocks no nudge", plan_fixes.nudged,
     (PANELLED, {"rows": [*CROWDED_ROWS["rows"], {"id": "wall_panel", "anchor": "on:hull"}]}), ANYTHING,
     {"items": Meets(lambda items: items[1][1:3] == [3.6, 3.45])}),
    # a stove is stood on the floor clear of both; a railing on a floor grating too, a sandbag pile stays piled; the
    # longer pipe is cut off the corner one, a wall panel and a pipe at another height left, strings overhead and
    # frames hung over each other on a wall left. Fixed once, the plan says nothing more
    ("what is piled on its own row's though it does not pile is stood apart, runs on a wall parted",
     plan_fixes.kept_apart, (KITCHEN, KITCHEN_ROWS), [SAID, SAID, SAID], All(
         {"shapes": {"STOVE 2": {"base": 0.0}, "RAIL 2": {"base": 0.0}, "BAGS 2": {"base": 0.3},
                     "STRING 2": {"base": 6.5}, "FRAME 2": {"base": 1.2}}},
         Meets(lambda plan: laid_boxes(plan)["STOVE 2"][2:] == [0.8, 0.6] and not any(plan_fixes.overlapping(
             [laid_boxes(plan)["STOVE 2"][0] - 0.04, laid_boxes(plan)["STOVE 2"][1] - 0.04, 0.88, 0.68],
             laid_boxes(plan)[other]) for other in ("FRIDGE 1", "STOVE 1"))),
         Meets(lambda plan: not plan_fixes.overlapping(laid_boxes(plan)["RAIL 2"], laid_boxes(plan)["RAIL 1"])),
         Meets(lambda plan: holds(laid_boxes(plan), {
             "BAGS 2": [1.2, 1.1, 1.0, 0.5], "STRING 2": [0.0, 4.1, 6.0, 0.2], "FRAME 2": [3.1, 4.8, 0.5, 0.1],
             "PIPE 1": [1.45, 0.0, 3.55, 0.3], "PIPE 3": [4.6, 0.0, 0.6, 0.3], "PANEL 1": [0.0, 0.0, 6.0, 5.0]})),
         NO_DROPPED), []),
    ("a counted pipe cut off the corner one lays one fewer, said", plan_fixes.wall_runs_parted,
     (KITCHEN_PIPED, KITCHEN_ROWS), ANYTHING,
     {"shapes": {"PIPE 1": {"count": 7}}, "dropped": Exactly([{"item": "pipe", "why": "1 fewer of it laid, pipe 1 cut "
                                                                      "clear of the piece at its corner: 9 laid",
                                                               "laid": 9}])}),
    ("plans keep fixes a writing fixed before kept_apart again, free", unsettled_unparted,
     (KITCHEN_WRITTEN, KITCHEN_ROWS), True, None),
    ("settled again, it lays and says what kept_apart does, and wants no more", functools.partial(
        plans_pass.settled_again, None, "kitchen", parts=False), (KITCHEN_WRITTEN, KITCHEN_ROWS, None), [All(
            Meets(lambda again: (again["items"], again["fixes"]) == kept_apart_of(KITCHEN, KITCHEN_ROWS)),
            Meets(lambda again: not plans_pass.unsettled(again, KITCHEN_ROWS, parts=False))), ANYTHING], None),
    ("a piled stove with no free floor is taken off, its row's count no gap", plan_fixes.unpiled,
     (BOXED_IN, BOXED_ROWS),
     Exactly(["stove: stove 2 taken off, 1 more of it than the place's free floor holds (0.8 x 0.6 m each): 1 laid"]),
     All(Meets(lambda plan: "STOVE 2" not in laid_boxes(plan) and "STOVE 1" in laid_boxes(plan)),
         {"dropped": Exactly([{"item": "stove", "why": "1 more of it than the place's free floor holds (0.8 x 0.6 m "
                                                       "each): 1 laid", "laid": 1}])},
         Meets(lambda plan: not plan_checks.count_gaps(plan, {"rows": [{"id": "stove", "count": 2}]}, set())))),
    ("a fit that sends every concept box to the room's middle has three anchors", plan_checks.projection_anchors,
     SYMMETRIC, Meets(lambda anchors: len(anchors) == 3), None),
    ("such a fit is none", plan_fixes.projector, SYMMETRIC, None, None),
    # the ramp moves out of the dome as made; the lander's ramp up into its lander as drawn stays; a building made
    # past the plan's edge moves no stair
    ("a ramp in a building made larger than drawn moves out of it", plan_fixes.kept_apart, (DOMED, MADE_ROWS),
     Exactly(["ramp 1: moved 1.48 m out of dome 1 as it is made (10.0 m across, drawn 6.00 m)"]),
     {"stairs": [{"points": Meets(lambda ramp: min(point[1] for point in ramp) >= 11.05
                                  and [point[0] for point in ramp] == [5.5, 6.5, 6.5, 5.5])},
                 {"points": [[16.5, 7.0], [17.5, 7.0], [17.5, 9.0], [16.5, 9.0]]},
                 {"points": [[7.0, 17.0], [8.0, 17.0], [8.0, 19.0], [7.0, 19.0]]}]}, []),
    # each pipe in one of its row's on a wall is laid along a wall none of its row lies on, the nearest first; one with
    # no such wall left is more than the walls hold: taken off, said in `dropped`; the first on its wall, a pipe 3 m
    # up, a counted run of pipes and a crane spanning the hall stay as laid
    ("pipes laid in one another are six stacked gaps, each saying why", stacked_left, (GARAGE_PIPES, GARAGE_PIPE_ROWS),
     Meets(lambda left: len(left) == 6 and left[0]["words"].endswith(plan_fixes.WHY["stacked"])), None),
    ("a wall's runs of one row are spread along free walls, one past what the walls hold taken off",
     plan_fixes.wall_runs_spread, (GARAGE_PIPES, GARAGE_PIPE_ROWS),
     Exactly(["pipe 2: laid along the west wall, out of its row's others on its own",
              "pipe 3: laid along the east wall, out of its row's others on its own",
              "pipe: pipe 5 taken off, 1 more of it than the place's wall room holds (10 x 0.1 m each): 7 laid"]),
     All(Meets(lambda plan: holds(laid_boxes(plan), {
         "PIPE 1": [0.0, 0.0, 10.0, 0.1], "PIPE 2": [0.0, 1.0, 0.1, 10.0], "PIPE 3": [11.9, 1.0, 0.1, 10.0],
         "PIPE 4": [1.0, 11.9, 10.0, 0.1], "PIPE 6": [0.0, 0.0, 10.0, 0.1], "DUCT 1": [1.0, 0.0, 8.0, 0.2],
         "CRANE 2": [1.0, 3.0, 10.0, 1.0]}) and "PIPE 5" not in laid_boxes(plan)),
         {"dropped": Exactly([{"item": "pipe", "laid": 7, "why": "1 more of it than the place's wall room holds "
                                                                 "(10 x 0.1 m each): 7 laid"}])},
         Meets(lambda plan: plan_fixes.stack_gaps(plan, GARAGE_PIPE_ROWS) == [])), []),
    # the eave is raised a storey over that floor, its rise kept; a floor at 0.1 m or a vault on its floor left
    ("an eave under an upper floor is raised a storey over it, its rise kept", plan_fixes.eaves_raised, (EAVED,),
     Exactly(["dome roof 1: its eave raised from 2.8 m to 5.8 m, a storey (2.8 m) over its upper floor at 3 m"]),
     {"roofs": [{"top": 9.2}]}),
    ("a floor at 0.1 m raises no eave", plan_fixes.eaves_raised, (eaved(0.1, {"kind": "dome", "eave": 2.5,
                                                                             "top": 3.5}),), [],
     {"roofs": [{"eave": 2.5}]}),
    ("a vault on its floor is left", plan_fixes.eaves_raised, (eaved(0.0, {"kind": "vault", "eave": 0.0, "top": 3.2}),),
     [], {"roofs": [{"eave": 0.0}]}),
    # the stairs row taken off where the plan draws flights, a staircase its railing stands on and a railing kept
    ("a plan with no flights keeps its stairs rows", plan_fixes.stair_rows_dropped,
     ({**STAIRS_WALLED, "stairs": []}, STAIR_ROWS), [], None),
    ("the stairs row is taken off where the shell builds the plan's flights", plan_fixes.stair_rows_dropped,
     (STAIRS_WALLED, STAIR_ROWS), Exactly(["stairs: taken off, the shell builds the plan's 1 flights"]),
     {"rows": Exactly({"ON THE WALLS AND CEILING": ["outer_wall"], "STAIRCASE 1": ["staircase"]}),
      "dropped": Exactly([{"item": "stairs", "why": "the shell builds the plan's 1 flights"}])}),
    # a thing on a flight as made moved off it on its own level, one with no such floor left a gap, one drawn on the
    # flight (a cart on its ramp) and one made past the plan (a hall's face) left
    ("a thing on a flight as made moves off it on its own level; the rest left, the bed a flight gap",
     plan_fixes.off_flights, (BEDS, BED_ROWS), Meets(lambda moved: len(moved) == 1
                                                     and moved[0].startswith("chair 1: moved")), All(
         Meets(lambda plan: (lambda chair: chair[1] + 0.5 <= 4.6 and not plan_fixes.crossing(numpy.array(
             [[chair[0] - 0.5, chair[1] - 0.5], [chair[0] + 0.5, chair[1] - 0.5], [chair[0] + 0.5, chair[1] + 0.5],
              [chair[0] - 0.5, chair[1] + 0.5]]), numpy.asarray(FLIGHTS[0]["points"])))(
             [laid_boxes(plan)["CHAIR 1"][0] + 0.15, laid_boxes(plan)["CHAIR 1"][1] + 0.15])),
         Meets(lambda plan: holds(laid_boxes(plan), {"BED 1": [2.5, 2.5, 0.5, 0.5], "CART 1": [0.5, 3.8, 0.4, 0.4],
                                                     "HALL 1": [1.25, 1.0, 0.5, 0.5]})),
         Meets(lambda plan: [gap["item"] for gap in flight_gaps_left(plan, BED_ROWS)] == ["BED 1"] and
               flight_gaps_left(plan, BED_ROWS)[0]["words"].endswith(plan_fixes.WHY["flight"])))),
    ("a bed with no such floor whose row lays another is taken off, said in `dropped`", plan_fixes.off_flights,
     (BEDS_ROWED, BED_ROWS), Exactly(["bed: bed 1 taken off, 1 more of it than its level's floor clear of the stairs "
                                      "holds (up to 5 x 5 m as made each): 1 laid"]), All(
         {"items": Meets(lambda items: [item[0] for item in items] == ["CHAIR 1", "CART 1", "HALL 1", "BED 2"]),
          "dropped": Meets(lambda dropped: dropped[0]["laid"] == 1)},
         Meets(lambda plan: plan_fixes.flight_gaps(plan, BED_ROWS) == []))),
    ("what the plan places on a thing taken off goes too, its row laying another, said", plan_fixes.off_flights,
     (potted_beds(True), POTTED_ROWS), Meets(lambda said: said[-1] == "pot: pot 1 taken off, its holder was dropped: "
                                                                      "1 laid"),
     All(Meets(lambda plan: "POT 1" not in laid_boxes(plan) and laid_boxes(plan)["POT 2"] == [3.7, 0.2, 0.3, 0.3]),
         {"dropped": Meets(lambda dropped: dropped[-1] == {"item": "pot", "why": "its holder was dropped: 1 laid",
                                                           "laid": 1})})),
    ("a row's last on a thing taken off stays", plan_fixes.surplus_dropped,
     (POTTED_ONE, POTTED_ROWS, [POTTED_ONE["items"][1]]),
     Meets(lambda said: said[-1].startswith("bed: bed 1 taken off")),
     All(Meets(lambda plan: laid_boxes(plan)["POT 1"] == [2.6, 2.6, 0.3, 0.3]),
         {"dropped": Meets(lambda dropped: [entry["item"] for entry in dropped] == ["bed"])})),
    # a run is laid as long as its pieces as made, clear of a suit standing low by a wall, its count what a free floor
    # within reach holds, said in `dropped`; a run that holds its pieces is left
    ("runs are laid as long as their pieces as made, clear of what stands by them, cut to their free floor",
     plan_fixes.runs_laid_out, (SACKS, SACK_ROWS), [SAID, SAID, SAID], All(
         {"shapes": {"BAGS 1": {"count": 4}, "BAGS 2": {"count": 2}, "BAGS 4": {"count": 3}}},
         Meets(lambda plan: laid_boxes(plan)["BAGS 2"] == [3.5, 3.0, 1.3, 0.5]),  # it holds its two
         Meets(lambda plan: laid_boxes(plan)["BAGS 1"][2:] == [2.4, 0.4] and not plan_fixes.overlapping(
             laid_boxes(plan)["BAGS 1"], laid_boxes(plan)["SUIT 1"])),  # off the suit, as long as its four as made
         Meets(bags_three_cut),
         Meets(lambda plan: laid_boxes(plan)["BAGS 4"][1] >= 4.0)), []),  # drawn past the outline, kept past it
    # a run hung from the roof is hung end to end along the walls under it, nearest first, as many a wall as its face
    # holds; lamps hung in a cluster are no run and stay
    ("a run hung from the roof is hung along the walls under it", plan_fixes.hung_runs_laid_out,
     (HUNG_HALL, HUNG_ROWS), [SAID], All(
         Meets(lambda plan: {item[0]: (item[1:5], plan["shapes"][item[0]].get("count")) for item in plan["items"]} == {
             "CABLES 1": ([1.0, 0.1, 4.0, 0.1], 2), "LAMPS 1": ([2.5, 1.5, 0.5, 0.5], 3),
             "CABLES 2": ([0.1, 1.0, 0.1, 2.0], 1), "CABLES 3": ([5.8, 1.0, 0.1, 2.0], 1),
             "CABLES 4": ([1.0, 3.8, 4.0, 0.1], 2)}), NO_DROPPED), []),
    # a ramp laid through a wall is taken off, one laid clear of the walls left
    ("a ramp the holders lay up through a wall is taken off", plan_fixes.ramps_walled,
     (loft_ramp(True), {"rows": [RAMP_ROW]}),
     Exactly(["ramp: ramp 1 taken off, 1 laid up to a raised level through a wall: 0 laid"]), {"items": []}),
    ("a ramp laid clear of the walls is left", plan_fixes.ramps_walled, (loft_ramp(False), {"rows": [RAMP_ROW]}), [],
     {"items": [ANYTHING]}),
    ("a run clear of the ramp as drawn, in it where the holders lay it, is moved out of it", plan_fixes.runs_laid_out,
     (LOFT_BAGGED, {"rows": [RAMP_ROW, SACK_ROWS["rows"][0]]}), [SAID],
     {"items": Meets(lambda items: not plan_fixes.overlapping(items[1][1:5], [2.0, 2.4, 2.0, 1.2]))}),
    # the things of a row stood on a top are cut to those that stand side by side along it as made, the nearest its
    # middle kept, the rest said in `dropped`; as many as fit are all kept
    ("five 0.5 m monitors on a 2 m desk are cut to the three nearest its middle", plan_fixes.tops_cut,
     (console_of(5), MONITOR_ROWS), ANYTHING,
     {"items": Meets(lambda items: [item[0] for item in items][1:] == ["MONITOR 2", "MONITOR 3", "MONITOR 4"]),
      "dropped": Exactly([{"item": "monitor", "why": "2 more of it than its holders' tops hold side by side as made: "
                                                    "3 laid", "laid": 3}])}, []),
    ("three that fit are all kept", plan_fixes.tops_cut, (console_of(3), MONITOR_ROWS), [], All(
        {"items": Meets(lambda items: [item[0] for item in items][1:] == ["MONITOR 1", "MONITOR 2", "MONITOR 3"])},
        NO_DROPPED), []),
]

