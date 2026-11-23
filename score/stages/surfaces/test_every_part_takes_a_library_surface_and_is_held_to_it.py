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
- scene_library.py: `return {**found, GLASS_KIND: GLASS_SHELL_WORDS} if shell_parts.glazes(plan, rows) else found` ->
  `return found`  -> every_part_takes_a_library_surface_and_is_held_to_it (a glass roof asked no glass kind)
- scene_library.py: `variant["opacity"] = CLEAR_GLASS` -> `pass`  -> every_part_takes_a_library_surface_and_is_held_to_it
  (the shell's glass drawn opaque)
- scene_library.py: `GLASS_KIND in kinds and bool(` -> `False and bool(`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (a glass kind answered with paint passes)
- registry.py: `if standing is None:` -> `if True:`  -> every_part_takes_a_library_surface_and_is_held_to_it (a second
  proposal stands as first proposed)
- registry.py: `return re.sub(r"[^a-z0-9]+", "_", name.lower())` -> `return re.sub(r"[^a-z0-9]+", "_", name)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (names alike but for case)
- place_line.py: `record["proposed"] = standing["spec"]` -> `record["proposed"] = row["proposed"]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- surface_data.py: `return not path(place).exists() or bool(takes(place))` -> `return not path(place).exists() or not
  takes(place)`  -> every_part_takes_a_library_surface_and_is_held_to_it
- __init__.py: `("finish-route-palette", scene_library.ROW, "surfaces-parts"), paid=True` -> `(scene_library.ROW,
  "surfaces-parts"), paid=True`  -> every_part_takes_a_library_surface_and_is_held_to_it
- __init__.py: `route_data.shape_files, selects=True),` -> `route_data.library_files, selects=True),`  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- __init__.py: `after=(), applies=data.paints, **more):` -> `after=(), applies=lambda place: True, **more):`  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- surface_gates.py: `except (FileNotFoundError, KeyError, json.JSONDecodeError) as missing:` -> `except (KeyError,
  json.JSONDecodeError) as missing:`  -> every_part_takes_a_library_surface_and_is_held_to_it
- bake_check.py: `(colour[:, 0] < BLOTCH_L) & (far > BLOTCH_DELTA_E)` -> `(colour[:, 0] < BLOTCH_L)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- bake_check.py: `if finish.get("measured_lab") is not None and not finish.get("cover"):` -> `if
  finish.get("measured_lab") is not None:`  -> every_part_takes_a_library_surface_and_is_held_to_it
- bake_check.py: `name = route_settings.settings_name(finish["surface"], settings) if settings else finish["surface"]`
  -> `name = finish["surface"]`  -> every_part_takes_a_library_surface_and_is_held_to_it
- bake_check.py: `if seen > ORDER_L and baked < -ORDER_BAKED:` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- bake_check.py: `if apart >= 1: return []` -> `if apart >= 0: return []`  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- place_line.py: `band = wide if not tall else min(FOOT_BAND, FOOT_BAND_METRES / tall) * height` -> `band = wide`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (fluid shelves in the capped band)
- place_line.py: `if record["feet"] == 2:` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (a fuel tank on two cradle feet)
- place_line.py: `if band < wide: # then` -> `if False: # then`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (an access stair's legs over the narrow band)
- place_line.py: `if found_row["id"] == row and stands(found_row` -> `if stands(found_row`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the claimed rack row; laid_shell)
- place_line.py: `for take, report in found.items() if report.get("feet", {}).get("refused")]` -> `for take, report in
  found.items() if False]`  -> every_part_takes_a_library_surface_and_is_held_to_it (a refused tank fails by name)
- place_line.py: `if row.get("group") == "kit: floor" or row.get("route") == "ground":` -> `if row.get("route") ==
  "ground":`  -> every_part_takes_a_library_surface_and_is_held_to_it (STANDING: gh_seat)
- place_line.py: `if unknown: raise` -> `if False: raise`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the crane-r1 take: its baked folder's dark_panel)
- inside/paint_take.py: `return os.waitstatus_to_exitcode(status), usage.ru_maxrss / 1e6` -> `return status,
  usage.ru_maxrss / 1e6`  -> every_part_takes_a_library_surface_and_is_held_to_it (the crane-r1 take: its paint killed)
- place_line.py: `*inventories, *models, *(REPO` -> `*inventories, *(REPO`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the crane-r1 take: its paint job)
- bake_check.py: `nearest = min(nearest, float(np.linalg.norm(baked - (worn + share * toward))))` -> `nearest =
  min(nearest, float(np.linalg.norm(baked - worn)))`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its ON_SURFACE "the wreck's white hull dirtied" row)
- bake_check.py: `worn = clean + share_worn * (bare - clean) if bare is not None else clean` -> `worn = clean`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its ON_SURFACE "hazard trim worn" and "worn 0.6 toward
  bare" rows)
- bake_check.py: `order = np.argsort(colour, axis=0)` -> `order = np.repeat(np.argsort(colour[:, 0])[:, None],
  colour.shape[1], axis=1)`  -> every_part_takes_a_library_surface_and_is_held_to_it (its AREA_MEDIANS rows)
- bake_check.py: `owners[chosen] = np.where(found >= 0, chosen[np.maximum(found, 0)], chosen)` -> `owners[chosen] =
  chosen`  -> every_part_takes_a_library_surface_and_is_held_to_it (RAY_NAMED: the bowl by its texel)
- uv_layout.py: `return -0.5 * (` -> `return 0.5 * (`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (LAYOUTS: mirrored)
- uv_layout.py: `return shares, int((counts > 1).sum()), int((counts > 0).sum())` -> `return shares, 0, 1`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (LAYOUTS: overlap)
- uv_layout.py: `and not (one_surface and measure == "thin")` dropped, or `== 1` -> `<= 2` (judge_layout)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the sticky note fails, or the frame
  passes); `not (one_surface and measure == "thin")` -> `not one_surface`  -> the same (its overlap passes)
- uv_layout.py: `keys = np.concatenate([geometry["positions"], geometry["uvs"]], axis=1)` -> `keys =
  np.arange(len(geometry["positions"]))[:, None]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the split corner)
- inside/layout_fit.py: `"overlap": float((counts > 1).sum() / max(int((counts > 0).sum()), 1)),` -> `"overlap":
  0.0,`, or `(width < THIN_TEXELS)` -> `(width < 0)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the bake's measure is the check's)
- inside/layout_fit.py: `and side * 2 <= largest` dropped, or `rounds is not None and rounds < UNFOLD_ROUNDS` dropped,
  or `(TARGET if rounds else LIMIT)` -> `TARGET`, or `found["thin"] > LIMIT or` dropped, or `polygons[found["shared"]]`
  -> `polygons`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (NEXT_STEPS rows, the folded faces)
- __init__.py: `"layout_fit.py")},` -> `)},`, or `return dataclasses.replace(row, make=bake_fitted.make_bake)` ->
  `return row`, or inside/paint_fit.py: `subprocess.run(fitted, check=True)` -> `subprocess.run(chunky, check=True)`,
  or bake_fitted.py: `route_bake.SCRIPT = SCRIPT` dropped  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the bake's layout_fit row)
- bake_check.py: `surface = ray_surfaces(geometry, laid, codes, entry["size"], sampled)` -> `surface =
  np.full(len(middles), -1)`  -> every_part_takes_a_library_surface_and_is_held_to_it (RAY_NAMED rows)
- bake_check.py: `found.append(round(float(chosen[:, 1].min() - low[1]), 3))` -> `found.append(0.0)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (STANCES)
- place_line.py: `if gaps.max() > most:` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BASES, HALLS)
- base_level.py: `if report["feet"] < ON_FEET:` -> `if True:` (a take on its feet has its overhang brought down), or
  bake_check.py: `or record.get("on_feet", 0) >= STANCE_FEET and down >= 3` dropped (on_stance)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the stool, the rover's stance; 2026-11-22)
- base_level.py: `feet.level = lambda *arguments: on_floor(*arguments) or level(*arguments)` -> `pass` (floored: the
  wheels stretched down to the lone leg), or `turned[np.isfinite(near) & under, 1] = level` -> `pass` (the lone leg
  left under the floor), or `or cut <= tolerance` dropped (feet on one leaning plane with none
  lone turned), or `if up_tilt(turned, faces) > up_tilt(points, faces):` -> `if False:` (a level body tipped onto its
  wheels), or `if TURNS:` -> `if False:` (boxed: a turned take's corners cut off)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (FLOORS; the rover's wheels, score #156, 2026-11-22)
- base_level.py: `min(rest[-2], cap)` -> `rest[-2]` (capped), or `return (found, record) if record["rise"] is not None
  else capped(step, cap)(points, *rest)` -> `return capped(step, cap)(points, *rest)` (capped_plane), or
  `place_line.levelled_feet = levelled_feet` -> `pass` (held), or `setattr(place_line, name, step)` -> `pass`
  (capped_base), or inside/paint_fit.py: `"score/stages/surfaces/base_level.py"` -> `".../place_line.py"`, or
  __init__.py: the declared `base_level.py` -> `place_line.py`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BASES, HALLS)
- flat_fit.py: `if not flat(size):` -> `if True:` (fitted_size), or `laid[thin] = min(laid[thin],
  depth_bound(size[thin]))` -> `pass` (face_fit), or `bake_job.fitted_size = fitted_size` -> `pass` (held), or
  inside/paint_fit.py: `"score/stages/surfaces/flat_fit.py"` -> `".../route_bake.py"`, or __init__.py: the declared
  `flat_fit.py` -> `route_bake.py`, or flat_fit.py drops `LIBRARY_TOOLS` from its sys.path (the bake job's own
  interpreter cannot import library)  -> every_part_takes_a_library_surface_and_is_held_to_it (FACE_FITS, the frame, the crate rows)
- place_line.py: `if len(under) < 3 or rise <= tolerance or` -> `if True or`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (a hut slopes as one plane)
- place_line.py: `if normal[1] > -1e-6: # no face` -> `if True: # no face`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (a tall cabinet's base step)
- place_line.py: `and not tumble.keeps_pose(row, ...)` dropped from stands  -> every_part_takes_a_library_surface_and_is_held_to_it (STANDING)
- place_line.py feet_rows `if HOME in inputs and bake_job.code_built(...)` -> `if False`  -> every_part_takes_a_library_surface_and_is_held_to_it (a code build)
- place_line.py stands `(row.get("anchor") or "") in` -> `row.get("anchor", "") in`  -> every_part_takes_a_library_surface_and_is_held_to_it (a null anchor)
- place_line.py: `if data.get("foot_traffic", True):` -> `if True:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its UNWALKED rows)
- place_line.py: `CLASSES = "gpu-24gb"` -> `CLASSES = "gpu-24gb,gpu-48gb"`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its RENTED rows)
- library_reads.py: `for name in entry["variants"]] if bakes else []` -> `for name in entry["variants"]]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its KEY_MOVES "a surface variant added anywhere" row)
- library_reads.py: `"details": {kind: details.get(kind) for kind in kind_names}}` -> `"details": {}}`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its KEY_MOVES "kind's details" row)
- library_reads.py: `"library": (wide["library"], library_part(kinds(record), bakes)),` -> `"library": wide["library"],`
  -> every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_BY_PART rows)
- library_reads.py: `if why:` -> `if False:`  -> every_part_takes_a_library_surface_and_is_held_to_it (a bake model
  with no written entry declared missing by name)
- carry.py: `if record.get("uncommitted", True) or not record.get("commit"):` -> `if not record.get("commit"):`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its WHY_NOT rows)
- carry.py standing: `if record is None: return None, f"its accepted output` -> `if False:` (why_not read off a None
  record)  -> every_part_takes_a_library_surface_and_is_held_to_it (an accepted output with no record in this store)
- carry.py: `if not str(proof.get("no-ops", {}).get(name, "")).strip()]` -> `if False]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PROOFS rows)
- carry.py: `str(folder), commit],` -> `str(folder), "HEAD"],`  -> every_part_takes_a_library_surface_and_is_held_to_it
  (codes_at at 548ab076 and its parent)
- props/same_content.py: `return PROPS_HOME.joinpath(*parts[index + 1:])` -> `return path`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONTENT_KEPT closeup moved by path text alone)
- props/same_content.py: `return files[name]` -> `return str(path)` (a closeup whose picture really changed kept), or
  its `if not files.get(name): raise` dropped (a record with no hash read by today's bytes on disk)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONTENT_KEPT closeup rows)
- carry.py: `if contents[0] != contents[1]:` -> `if False:`  -> every_part_takes_a_library_surface_and_is_held_to_it
  (its CONTENT_KEPT rows whose content differs); carry.py changes_by_content `return None, None, why` ->
  `return None, {}, why`  -> the same (a content proof, even an empty one, given beside a why)
- rough_model/same_content.py: `"floor": plan["floor"], ` dropped  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONTENT_KEPT "a plan with another floor" row); carry.py
  `if any(record.get(part) != keyed.get(part) for part in CONTENT_SAME):` -> `if False:`  -> the same (its "seed
  moved too" row)
- people/same_content.py: `entry["model"] = in_output(entry["model"])` -> `pass`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONTENT_KEPT people-made moved by its model path alone);
  carry.py `CONTENT_SAME = (...)` -> `()`  -> the same (its "params moved too" row)
- score/graph/__init__.py Runner.same_earlier: `return hasattr(stage.files, "same_earlier") and
  stage.files.same_earlier(self, stage, place, record, keyed)` -> `return True`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONTENT_KEPT rows: a row with no content rule held only
  while its earlier outputs stand)
- finish_parts.py: `found[reached] = face_label[source[reached]]` -> `found[reached] = 0`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its shared sphere's walked faces)
- finish_parts.py: `host = np.flatnonzero(hosts & (face_label == finish))` -> `host = np.flatnonzero(hosts)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its MERGED "loose bit" row)
- finish_parts.py: `part_of[lost] = island[lost[0]]` -> `part_of[lost] = island[lost]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its MERGED "crumbs only" row)
- finish_parts.py: `return kept_finishes(face_label, labels.without_crumbs(mesh, smoothed), mesh.area_faces)` ->
  `return labels.without_crumbs(mesh, smoothed)`, or kept_finishes `lost = np.union1d(..., shrunk)` -> `lost =
  np.setdiff1d(np.unique(before), np.unique(after))`  -> every_part_takes_a_library_surface_and_is_held_to_it (its
  shared sphere's cleaned dots and KEPT rows)
- finish_parts.py: `stray = ~standing & ~np.isclose(area, piece_area[piece[face_of]]) & np.isin(finish,
  finish[standing])` -> `stray = ~standing & ~np.isclose(area, piece_area[piece[face_of]])`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its STRAYS rows)
- finish_parts.py: `standing = (area >= least) | fragmented_largest(area, finish, least)` -> `standing = area >= least`,
  or fragmented_largest `return (first | (area >= crumb)) & (area < least) & (total[finish] >= least)` -> `return
  (first | (area >= crumb)) & (area < least)`, or `(first | (area >= crumb))` -> `first` (the hub's right console's
  screens painted as its steel)  -> every_part_takes_a_library_surface_and_is_held_to_it (its STRAYS rows)
- finish_parts.py: `own = np.where(details | kept, part_of.max() + 1 + island, part_of)` -> `own = part_of`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its BLOTCHES detail rows and PARTED rows); `details |
  kept` -> `details` (a screen holding a loose bit or a crumb read as a blotch), or `stray = found["stray"] +
  taken_crumbs(...)` -> `stray = found["stray"]` (the crumb a screen's part took in no stray)  -> the same test (its
  PARTED rows)
- finish_parts.py: `areas[seen & (face_label == label)].sum()` -> `areas[seen].sum()`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its shared sphere's agreement)
- finish_parts.py: `own = finish.get("colour") and finish["surface"] == finish.get("listed_surface", finish["surface"])`
  -> `own = finish.get("colour")`  -> every_part_takes_a_library_surface_and_is_held_to_it (its OUT_OF_ORDER "moved off
  its listed surface" row)
- finish_ask.py: `if error.code not in REFUSED: raise` -> `if False: raise`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its GENERATED rows asked again)
- finish_parts.py: `if nearest_apart <= COLOUR_DELTA_E:` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- finish_parts.py: `if not reordered(lighter, darker, every, lightness, wide) and wide:` -> `if not reordered(lighter,
  darker, every, lightness, wide) and False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its IN_ORDER water tank row)
- finish_parts.py: `if fit and (wide or fit[0] < close_up_apart(finish, every)):` -> `if fit and wide:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its IN_ORDER shelving row)
- finish_parts.py: `if apart > COLOUR_DELTA_E and coloured_cover(finish, every):` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED beacon row)
- finish_parts.py: `and meaning_kept(record, listed, every[name]))` -> `)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- finish_parts.py: `and meaning_kept(finish, listed, spec)]` -> `]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED rows)
- finish_parts.py: `return in_named_colour(named, lab, recipe)` -> `return True`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED rows)
- finish_parts.py: `return painted["recipe"] == listed["recipe"] and hue_kept(` -> `return True and hue_kept(`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- finish_parts.py: `if not look_kept(finish["finish"], ...):` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- finish_parts.py: `judged = carriers or [finish ...]` -> `judged = [finish ...]` (the largest alone)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its MEANING dome rows)
- finish_parts.py: `or in_named_colour(named, finish["looks"]["painted"]["lab"], ...)` -> `or True`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- score/stages/__init__.py meaning_checked: `if row.name != "surfaces-parts":` -> `if True:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- finish_ask.py: `entry = dict(entry, surface=names[codes.index(entry["surface"])])` -> `entry = dict(entry)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (a reply parsed to library names)
- route_views.py: `if record["seen_share"] < SEEN_LEAST * reachable:` -> `if record["seen_share"] < SEEN_LEAST:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its SEEN rows)
- route_views.py: `while candidates and len(angles) < MOST_VIEWS and not seen.all():` -> `while False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its open tube)
- route_views.py: `if record.get("model") is None: return [f"{take}: no raw take` -> `if False: return [f"{take}: no raw
  take`  -> every_part_takes_a_library_surface_and_is_held_to_it (its VIEWS_JUDGED rows)
- route_list.py: `return (level, cause) if level in levels and cause else (None, None)` -> `return (level, cause) if
  level in levels else (None, None)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LISTED batch of two takes)
- route_split.py: `if found["unassigned"] > UNASSIGNED_MOST:` -> `if False:`, and apart -> `if found["unassigned"]
  > 0:` (no tolerance) and -> `if found["unassigned"] > 2 * UNASSIGNED_MOST:` (loosened past the measure)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its SPLIT_SHARES rows and the LISTED row leaving the blue box
  out)
- route_split.py: `own = np.where((votes.sum(1) > 0) & ~tied, votes.argmax(1), -1)` -> `own = np.where(votes.sum(1) >
  0, votes.argmax(1), -1)`; and, apart, `votes[seen, label[seen]] += square * (` -> `votes[seen, label[seen]] += 1.0 * (`
  -> every_part_takes_a_library_surface_and_is_held_to_it (its SPLIT_VOTES and SQUARED rows)
- route_split.py `split_take`: `count = len(listed["finishes"])` -> `count = len({entry["settings"]["token"] for entry
  in listed["finishes"]})` (the finishes counted by their colour, not their labels)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LISTED row of the blue box listed in red)
- route_views.py `laid_close_up`: `if fit < cast.CLOSE_UP_FIT:` -> `if True:` (no close-up ever laid)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LISTED row of a finish only the close-up shows,
  2026-10-29)
- route_views.py: `centres = merged_centres(every, fine_centres(every, seed))` -> `centres = kmeans2(every,
  REGIONS, seed=seed, minit="++")[0]`  -> every_part_takes_a_library_surface_and_is_held_to_it (its red among
  greys and rust)
- route_views.py: `every_faces[CLOSE_UP], every_colours[CLOSE_UP] = laid` -> `pass`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LISTED row of a finish only the close-up shows)
- route_split.py: `return close_up_only(votes, per_map)` -> `return votes`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LISTED row of a finish only the close-up shows)
- route_split.py `voted_finishes`: `finish_parts.walked(mesh, behind(mesh, own, voted))` -> `finish_parts.walked(mesh,
  own)`; and, apart, `return hidden_joined(mesh, finish_parts.merged_islands(` -> `return (lambda found, voted:
  found)(finish_parts.merged_islands(`  -> every_part_takes_a_library_surface_and_is_held_to_it (its SPLIT_SHELL rows,
  #173)
- route_list.py: `failing.append(f"{take}: no finish list" + (f" ({asked['unanswered'][take]})"` ->
  `failing.append(f"{take}: no finish list" + ("" if True else f" ({asked['unanswered'][take]})"`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LISTED row of the batch that ended)
- route_list.py: `answers.update(followed_up(answers, bodies, ...))` dropped, and apart, followed_up `<
  first[take][1]:` -> `<= first[take][1]:`  -> every_part_takes_a_library_surface_and_is_held_to_it (its LISTED
  rows asked once more)
- route_parts.py: `np.save(folders["out"] / "parts.npy", part_of.astype(np.int32))` -> `np.save(folders["out"] /
  "parts.npy", part_of[:1].astype(np.int32))`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its parted LISTED rows)
- route_parts.py `finish_colours`: `if fit >= cast.CLOSE_UP_FIT:` -> `if False:` (the views' light-baked texture
  read, never the close-up)  -> every_part_takes_a_library_surface_and_is_held_to_it (its LISTED row of the shaded
  texture)
- route_parts.py: `and not lamps.on_stem({"size": built.get("size")})` -> `and True`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIT_TAKES and LIT rows); so does `zip(checked, lit if
  any(lit) else [True] * len(checked))` -> `zip(checked, [True] * len(checked))` (the light bar's metal end caps
  glowing)
- route_bake.py: `surface=route_settings.settings_name(record["surface"], record["settings"])` ->
  `surface=record["surface"]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its bake: the spec of each part)
- route_bake.py: made_of's `return out / f".bake-{take}-made"` -> `return out / "made"`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its bake jobs: each job's outputs its own); in make_bake, `gathered(made_of(out, take), out / "made")` ->
  `pass`  -> every_part_takes_a_library_surface_and_is_held_to_it (its bake gathered where its readers find it)
- route_bake.py: in stood_square `if turned < made:` -> `if False:`, or `if CLOSEUP in inputs:` -> `if False:`; or
  in card_job drop `**{CLOSEUP: str(path) for path in closeup}`  -> every_part_takes_a_library_surface_and_is_held_to_it
  (its STAND_SQUARE close-up rows and the card job's listing)
- take_outline.py: `* 1.05` -> `* 1.2` in `silhouette`; or `ndimage.binary_fill_holes(labels == largest)` -> `labels
  == largest` in `cut`; or in `look_down`, `closeup_check().look_down(size)` -> `15.0`; or in `look_downs`,
  `[stated, shown_look_down(target, size)] if` -> `[stated] if`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its OUTLINE_SIZES rows)
- route_bake.py: laid_shell's `if key != "route"` -> `if True`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the claimed rack row; laid_shell)
- route_bake.py: own_parts' `return folder` -> `return short["parts"]`; or `dict(job_head(data, short, {take:
  records[take]}),` -> `dict(job_head(data, short, records),`; or card_job's `for name, path in world.items()}` ->
  `for name, path in short.items()}`  -> every_part_takes_a_library_surface_and_is_held_to_it (its bake jobs: an
  unchanged take's job moved with another take's parts)
- route_check.py: `library.by_library = lambda name: {**palette_library.specs(palette), **baked}` -> `library.by_library
  = lambda name: {**palette_library.specs(palette)}`  -> every_part_takes_a_library_surface_and_is_held_to_it (the spec the bake baked)
- route_recheck.py: `**({"colour": tokens[settings["token"]]} if settings.get("token") in tokens else {}),` deleted  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its WORDED rows)
- route_recheck.py: `wrong = failed(finishes, answers)` -> `wrong = []`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its RECHECKS rows)
- route_recheck.py: `if faults: found[take] = {"colour_faults"` -> `if False: found[take] = {"colour_faults"`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its RECHECKS row never asked)
- scene_palette.py: `tokens.setdefault(entry["token"], entry["colour"].lower())` -> `tokens[entry["token"]] =
  entry["colour"].lower()`  -> every_part_takes_a_library_surface_and_is_held_to_it (its PALETTE_ASKS rows)
- scene_palette.py: `if parsed["wear"] not in levels or parsed["dirt_token"] not in tokens:` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PALETTE_ASKS rows)
- scene_palette.py: `left_out="Leave out colours only the people in it wear. " if own else "",` -> `left_out="Leave out
  colours only the people in it wear. ",`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PALETTE_ASKS rows)
- scene_palette.py: `close_ups=CLOSE_UPS.format(count=len(close_ups)) if close_ups else "",` -> `close_ups="",`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PALETTE_ASKS rows)
- scene_library.py: `in (surface.get("colours") or {}).items() if setting in needs})` -> `in (surface.get("colours")
  or {}).items()})`, or `"required": list(settings),` -> `"required": [],` (schema; surface-library@tube's
  rusted_door_steel left its bare out, 2026-11-09)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows)
- body_faces.py: `"required": needs,` -> `"required": [],`  -> every_part_takes_a_library_surface_and_is_held_to_it (its FACES moon row)
- scene_library.py: `for kind in kinds if not found.get("kinds", {}).get(kind)]` -> `for kind in kinds if False]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows)
- scene_library.py: `parts.add("stair")` -> `pass`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows)
- scene_library.py: `for name, defaults in method["recipes"].items() if name not in PICTURED}` -> `for name, defaults in
  method["recipes"].items()}`  -> every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows, sheets)
- scene_library.py: `if recipe and row.get("noun"):` -> `if False:`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows)
- tools/props/library/library.py: `if missing: raise LibraryEmpty` -> `if False: raise LibraryEmpty`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the empty library)
- palette_library.py: `"stair": ("stairs", "stair", "steps", "ramp", "floor")}` -> `"stair": ("stairs", "stair",
  "steps", "ramp")}`  -> every_part_takes_a_library_surface_and_is_held_to_it (its SHELL_PARTS rows)
- route_ask.py: `compute.require_cleared(f"a Gemini batch ({caller})")` deleted  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its ASKED row of an uncached ask)
- route_ask.py: `if not all(google_spend.cache_path(finish_ask.LIST_MODEL, body).exists() for body in bodies.values()):`
  -> `if True:`  -> every_part_takes_a_library_surface_and_is_held_to_it (its ASKED rows the cache answers whole)
- route_ask.py: `google_spend.cache_path(finish_ask.LIST_MODEL, body).unlink(missing_ok=True)` -> `pass`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its ASKED row that does not parse)
- __init__.py: `route_data.shape_files, selects=True),` -> `route_data.shape_files),`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the object filter)
- __init__.py: `after=reads("finish-route-palette", scene_library.ROW, "surfaces-bake", "surfaces-paint",` ->
  `after=reads(scene_library.ROW, "surfaces-bake", "surfaces-paint",`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the rows' waits)
- bake_job.py: `if inline is None: raise NoEntry` -> `if inline is None: return {"name": model} raise NoEntry`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES: the model the data writes no entry for)
- bake_job.py: `return TURNS[min(TURNS, key=misfit)]` -> `return TURNS[0]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES: a take long along z for a row wide along x)
- bake_job.py: `return fitted_size(labelled, size, base)` -> `return size` (laid_size: stretched to its row), or
  `np.min(` -> `np.max(` (fit_within: past its row), or fit_within's `np.clip(scales, scale, scale * STRETCH_MOST)`
  -> `scale` (the monitor laid 0.32 m wide), or `FREE_MOST * float(size[free])` -> `float(size[free])` (bound
  by its depth again, 0.13 m wide), or flat_fit.py face_fit's `np.clip(size / found, ...)` -> `float(scale)` (the
  face 1.0 m wide), or refitted's `if fits else entry` -> `if False else entry`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES: the tunnel, the hanging row, the stool; REFITS; fit_within)
- route_bake.py: `if kept or not tumble.tumbled(laid):` -> `if True:`, or tumble.py: `return f"its design lays it
  lying ({said})"` -> `return None`  -> every_part_takes_a_library_surface_and_is_held_to_it (its STAND_SQUARE rows)
- bake_check.py: `and record["square"]["loose"] > tumble.LOOSE]` -> `and False]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its `stands square` verdict)
- tumble.py: `if built:` -> `if False:`, or route_bake.py `rules, rows, built)` -> `rules, rows)`; or tumble.py
  `square_turn`: `if order[1] == up or not keep_up)` -> `if True)`  -> every_part_takes_a_library_surface_and_is_held_to_it (its STAND_SQUARE rows: a code
  build, the L desk)
- tumble.py `hangs`: `return f"anchored {anchor}"` -> `return None`; or `NO_UP = ("ground debris", "cable")` ->
  `NO_UP = ("ground debris",)`; or `person`: `return row.get("route") == PEOPLE` -> `return False`; or bake_check.py
  `keeps_pose_of`: `or (entry.get("stood") or {}).get("kept")` dropped  -> every_part_takes_a_library_surface_and_is_held_to_it (its KEEPS_POSE
  rows, the lamp's STAND_SQUARE row, the undone valves)
- route_bake.py `squared_again`: `elif turned:` -> `elif False:`; or `square = not (...) and (not turned or degrees
  <= tumble.DEGREES)` -> `square = not (degrees > tumble.DEGREES and loose > tumble.LOOSE)`; or `elif measured <
  SQUARE_ROUNDS:` -> `elif False:`  -> every_part_takes_a_library_surface_and_is_held_to_it (its SQUARE_AGAIN rows)
- route_bake.py: `opening = min(inside, float(recess["wide"]) + room * (1.0 if room_side else 2.0))` -> `opening =
  min(inside, float(recess["wide"]))`  -> every_part_takes_a_library_surface_and_is_held_to_it (its DOORS row of the
  door hinged left at full open)
- route_bake.py: `depth = min(float(recess["depth"]), 2 * half - RECESS_BACK)` -> `depth = 2 * half + RECESS_OUT` (a
  tunnel), or `low[across], high[across] = middle - opening / 2, middle + opening / 2` -> the door's own `along`
  unkept  -> every_part_takes_a_library_surface_and_is_held_to_it (its DOORS rows: base's garage door, its back)
- route_bake.py: `inside = span - 2 * RECESS_BACK` -> `inside = span` (2026-10-29)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its DOORS rows of a door at its face's end)
- score/review/holders/__init__.py: `RECESS_WALL = 0.05` -> `RECESS_WALL = 0.0`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its DOORS row of a door at its face's end)
- bake_job.py: `if built or slender(size):` -> `if slender(size):` (laid_size)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES: a code build at its own section); -> `if False:`  -> that one and
  its slender row
- bake_job.py: `if own and lies(place_route.made_size(labelled, size, 0), size):` -> `if False and lies(...)`
  (measured_turn), or its `square_turn(..., keep_up=False)` -> `square_turn(...)` (the stand step's turn, which keeps
  the take's up)  -> every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES: a code build
  for a row that lies)
- surface_data.py: `"bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library"}` -> `"bake
  scripts": "{repo}/tools/props/library/inside", "library": "{data}/library", "details": "{data}/library/details.json"}`
  -> every_part_takes_a_library_surface_and_is_held_to_it (every place's bake from git)
- bake_job.py: `if person and not built` -> `if False` (entry_of), or `return tumble.person(row or {}) or
  person_take(take, inputs)` -> `return person_take(take, inputs)` (drawn_person)  -> every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES:
  the pilot, the officer)
- bake_job.py: `base = person_turn(labelled) if person else measured_turn(...)` -> `base = measured_turn(...)`
  (entry_of), or `return tumble.person(row or {}) or person_take(take, inputs)` -> `return tumble.person(row or {})`
  (drawn_person), or route_bake.py stood_square: `kept = tumble.PERSON if person else ...` -> `kept = ...`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (BAKE_ENTRIES: a people line look)
- body_faces.py: `for body in settings.checked(concept(store)["setting"])["bodies"] if body.get("kelvin") is None]` ->
  `for body in settings.checked(concept(store)["setting"])["bodies"]]`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its body-face rows)
- body_faces.py: `"style": environment_concept.style_now(),` -> `"style": "",`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its body-face rows, no concept locked)
- body_faces.py: `"recipe": {"type": "STRING", "enum": [recipe]},` -> `"recipe": {"type": "STRING", "enum":
  list(method["recipes"])},`  -> every_part_takes_a_library_surface_and_is_held_to_it (its FACES moon row)
- body_faces.py: `failing += [f"recipe {variant['recipe']} is no natural ground"] * (variant["recipe"] not in
  natural_grounds.RECIPES)` deleted  -> every_part_takes_a_library_surface_and_is_held_to_it (the off mars face)
- body_faces.py: `if recipe is None: raise ValueError` -> `if False: raise ValueError`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its FACES vesta row)
- claude_asks.py: `"finish-route-list", ` deleted from ROWS  -> every_part_takes_a_library_surface_and_is_held_to_it (its asks)
- claude_asks.py: `module.ask = gemini` -> `pass`  -> every_part_takes_a_library_surface_and_is_held_to_it (its asks)
- claude_asks.py: `again[take] = repaired(bodies[take], answer, off, levels)` -> `pass`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its REPAIRS rows)
- place_line.py: `return turn.T` -> `return None` in `recovered_turn`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PAINT_TURNS rows)
- place_line.py: `turn @ labels.raw_facing(take)` -> `turn` in `finished_frame`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PAINT_TURNS row of the raw take facing +Z)
- baked_colour.py: `and entry["off"] > OFF_SHARE` -> `and entry["off"] > 1.0`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONSOLES rows)
- baked_colour.py: `moved &= np.linalg.norm(seen - np.asarray(shade[1:]), axis=1) > OFF_AB` -> `pass`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONSOLES rows)
- route_paint.py: `("colour against the close-up", baked_colour.judge_colour)` -> `("colour against the close-up",
  place_line.judge_concept_colour)`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CONSOLES rows)
- scene_library.py: `+ (SHEET_WORDS if take["kind"] in sheets else "")` -> `+ ""` (kinds_of), or `"pile": ["second"]`
  dropped from data/library/materials.json's colour_settings  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows, sheets)
- scene_library.py: `+ (PICTURE_WORDS if shows_picture(...) else "")` -> `+ ""` (kinds_of), or `in DRAWN for name
  in found["kinds"][kind]` -> `in DRAWN or True for name in found["kinds"][kind]` (library_findings), or
  `for kind in found.get("picture_kinds", [])` -> `for kind, words in kinds.items() if PICTURE_WORDS in words` (a
  library accepted before the marking failed by it)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows, sheets)
- scene_library.py: `SHEET_FLAT, SHEET_MIDDLE = 0.05, 0.25` -> `0.1, 0.25` (the row's sheet rule off the bake's)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIBRARY_ASKS rows, sheets)
- bake_check.py: `max(min(size) / BAKE_THIN_VOXELS, surface)` -> `max(size) * BAKE_VOXEL_SHARE` in `bake_voxel`  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the lantern string's voxel)
- parts_kept.py: `return found if found["delta_e"] <= record["delta_e"] else record` -> `return found` (kit_kept)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- parts_kept.py: `finish.get("surface") in glowing and` -> `False and` (lit_kept)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIT_TAKES and LIT rows)
- parts_kept.py: `if record.get("picked"):` -> `if False:` (kit_kept); or `if finish.get("picked"):` -> `if False:`
  (pick_kept); or `if spec.get("recipe") == "glowing" and` -> `if False and` (glow_kept)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its CHECKED and MEANING rows)
- check_seen.py: `if surface.split(route_settings.SEPARATOR)[0] in glowing` -> `if False` (lit_as_light)  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- recheck_picks.py: `if apart > finish_parts.COLOUR_DELTA_E:` -> `if False:` (fitting); or `if picks:` -> `if
  False:` (make_parts); or `(out / batch_gaps.FILE).unlink(missing_ok=True)` -> `pass` (make_picks); or `or
  token_apart(...) > finish_parts.COLOUR_DELTA_E]` -> `or False]` (judge_picks)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PICKS and REMADE rows)
- recheck_picks.py: `if pick["token"] not in tokens:` -> `if False:` (placing); or `if highest >= count:` -> `if
  False:` (split_fits); or `OVERLAP = 0.5` -> `OVERLAP = 0.2`; or `return same[0] if len(same) == 1 else None` ->
  `return index` (finish_for)  -> every_part_takes_a_library_surface_and_is_held_to_it
  (its REMADE and FINISH_FOR rows)
- colour_picks.py: `return fits[0] if fits and fits[0][0] <= finish_parts.COLOUR_DELTA_E else None` -> `return
  fits[0] if fits else None` (nearest_token); or `if finish_parts.hue_kept(` -> `if True or finish_parts.hue_kept(`
  (nearest_token); or `if why != NOT_ASKED:` -> `if True:` (make_picks)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its PICKS and COLOUR_FITTING rows)
- __init__.py (the table): `make=colour_picks.make_picks,` -> `make=recheck_picks.make_picks,` (picks_applied)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (the picks row made through colour_picks.make_picks)
- __init__.py (the table): `make=recheck_picks.make_parts,` -> `make=row.make,` (picks_applied)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (its LIT_TAKES and LIT rows)
- check_seen.py: `"pieces": [...]` -> `"pieces": []` (laid_kit)  ->
  every_part_takes_a_library_surface_and_is_held_to_it
- feet_stand.py: `if refused == [feet.get("rests")] else None` -> `if False else None` (judge_feet)  ->
  every_part_takes_a_library_surface_and_is_held_to_it (FEET_JUDGED)
- feet_stand.py: `worst = max(worst, outside if outside > BALANCE else 0.0)` -> `worst = max(worst, 0.0)` (off_balance)
  -> every_part_takes_a_library_surface_and_is_held_to_it (a tipped seat)
- route_parts.py: `on_part = {name: faces[at] >= 0 and ...` -> `on_part = {name: faces[at] >= 0 ...` (any part)
  (placement) -> every_part_takes_a_library_surface_and_is_held_to_it (DECAL_MARKS: a mark printed past its part)
- route_parts.py: `/ inner` dropped (spanned) -> every_part_takes_a_library_surface_and_is_held_to_it (DECAL_MARKS:
  a label sized at its probes, not its box)
- finish_ask.py: `elif decal["ink"] != mark.get("ink"):` -> `elif False:` (marks_of) ->
  every_part_takes_a_library_surface_and_is_held_to_it (a many-ink logo printed from a one-ink decal)
- decal_library.py: `or row.get("state") == "withdrawn"` dropped (catalogue) ->
  every_part_takes_a_library_surface_and_is_held_to_it (a withdrawn decal offered)
- route_bake.py: `if image is None or ...` -> `if False:` (decals_on) ->
  every_part_takes_a_library_surface_and_is_held_to_it (a decal the library does not hold baked)
"""
import contextlib
import copy
import inspect
import io
import itertools
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
from score.adapters import compute  # noqa: E402
from score.review import holders, setting as settings  # noqa: E402
from score.stages import shapes_first, surfaces  # noqa: E402
from score.stages.assembly import fitting as assembly_fitting  # noqa: E402
from score.stages.surfaces import (bake_check, body_faces, carry, check_seen, claude_asks, decal_library,  # noqa: E402
                                   finish_ask, finish_parts,
                                   library_reads, palette_library, parts_kept, place_line, registry, route_ask,
                                   route_bake, route_cast,
                                   recheck_picks, route_check, route_data, route_list, route_paint, route_parts,
                                   route_recheck,
                                   route_settings, route_split, route_views, scene_library, scene_palette,
                                   surface_data, surface_gates)
from score.store import PROPS_HOME, Store, text_hash  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402

import bake_job  # noqa: E402  (place_line puts its folder and tools/props/library on the path)
import tumble  # noqa: E402
import baked_colour  # noqa: E402  (as route_paint imports it)
import library  # noqa: E402
import patchy  # noqa: E402  (on the path finish_parts gives)
import place_route  # noqa: E402
import route  # noqa: E402

# No designed place's hand-in (the home's design/, which the sandbox links) is read here: prepare's test holds those.
prop_data.DESIGN = surface_data.DESIGN = pathlib.Path(tempfile.mkdtemp()) / "no design"
surfaces.data.DESIGN = surface_data.DESIGN  # the table's own import of it (bare `surface_data`)
ROWS = {row.name: row for row in stages.STAGES}


# --- surfaces ---

def a_store():
    return Store.in_folder(tempfile.mkdtemp())


# A take's parts as the method named them, each with the new library surface it proposed or None, painted in turn
# into one store: (case, [(the method's surface, its proposal)], the proposal each part stands as (its index in the
# list: the first proposed, or the first named alike but for case; None where the part proposed none)).
PROPOSED = [
    ("a part takes the method's surface and its proposal stands in for it",
     [("dark_panel", None), ("galvanized_dull", {"name": "aluminium tape", "description": "shiny",
                                                 "why": "thinner than steel"})], [None, 1]),
    ("a second proposal stands as first proposed", [("galvanized_dull", {"name": "Aluminium tape, silver"}),
                                                    ("bare_steel", {"name": "Aluminium tape, silver"})], [0, 0]),
    ("names alike but for case stand as one entry", [("pipe_steel", {"name": "Polished Chrome"}),
                                                     ("bare_steel", {"name": "polished chrome"}),
                                                     ("brass", {"name": "Polished brass"})], [0, 0, 2]),
]


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
    """The seed tray's checks.json record, its printed_paper's near-black share measured from `rows` (blotch_share)."""
    colour = np.array([row[:3] for row in rows])
    reach = np.array([[flag == "1" for flag in row[4]] for row in rows])
    share = bake_check.blotch_share(colour, np.array([row[3] for row in rows]), np.ones(len(rows), dtype=bool), reach,
                                    [[surface] for surface in SEED_TRAY_SURFACES])
    return {"surfaces": {"printed_paper": {"share": 0.0117, "baked_lab": [77.7, -0.7, 7.7],
                                           "surface_lab": list(SEED_TRAY_SURFACES[1]), "delta_e": 1.5,
                                           "near_black": share}}}


def smudged(rows):
    """`rows` with the light triangles across the label's border turned black until a tenth of its area."""
    smudge, area = [], 0.0
    total = sum(row[3] for row in rows)
    for row in rows:
        if row[5] and row[0] > bake_check.BLOTCH_L and area < 0.1 * total:
            row, area = (0.0, 0.0, 0.0, *row[3:]), area + row[3]
        smudge.append(row)
    return smudge


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


def baked_record(surfaces, close_up, degrees=None):
    """A checks.json record of a model baked exactly on its surfaces ({surface: (share, L*a*b*)})."""
    return {"surfaces": {name: {"share": share, "baked_lab": list(colour), "surface_lab": list(colour),
                                "delta_e": 0.0, "near_black": 0.0} for name, (share, colour) in surfaces.items()},
            "close_up": close_up, "seen_degrees": degrees}


def labelled_close_up(finishes):
    """The close-up colours bake_check reads from a take's labels.json holding `finishes`."""
    with tempfile.TemporaryDirectory() as scratch:
        (pathlib.Path(scratch) / "labels.json").write_text(json.dumps({"finishes": finishes}))
        return bake_check.close_up_colours(pathlib.Path(scratch))


# The garage beacon's finishes: its red transparent dome measured pale pink on its brighter half (its highlights and
# what lies behind it), a cover judged by its own colour; a print off its listed colour, judged by its own colour but
# still in the close-up; the opaque knob of the same surface as the dome, compared.
DOME = {"finish": "Red transparent plastic", "surface": "red_plastic", "measured_lab": [70.8, 21.2, 11.5],
        "by": "its own colour", "cover": True}
LABEL = {"finish": "Printed label", "surface": "printed_paper", "measured_lab": [30.0, 5.0, 5.0], "by": "its own colour"}
KNOB = {"finish": "Red plastic", "surface": "red_plastic", "measured_lab": [40.0, 55.0, 40.0], "by": "the list"}
# astronaut-made (2026-10-23): boots with the list's settings bake by their settings' name (route_settings); a belt
# the colour check moved to another surface bakes under that surface's own name.
SUIT = {"token": "glass-grey", "roughness": 0.85, "metal": 0.0, "seed": 7}
BOOTS = route_settings.settings_name("suit_boots", SUIT)
BOOTS_FINISH = {"finish": "boots", "surface": "suit_boots", "listed_surface": "suit_boots", "settings": SUIT,
                "measured_lab": [33.1, 0.9, 7.6]}
BELT_FINISH = {"finish": "belt", "surface": "rubber_dark", "listed_surface": "suit_boots", "settings": SUIT,
               "measured_lab": [20.0, 0.0, 0.0]}
# Each take's finishes and the close-up colours they give: (finishes, close-up).
CLOSE_UPS = {
    "a covering dome": ([DOME], {}),
    "a dome and an off-colour print": ([DOME, LABEL], {"printed_paper": [30.0, 5.0, 5.0]}),
    "a dome and an opaque knob": ([DOME, KNOB], {"red_plastic": [40.0, 55.0, 40.0]}),
    "an uncovered dome": ([dict(DOME, cover=False)], {"red_plastic": [70.8, 21.2, 11.5]}),
    "boots by their settings, a belt moved": ([BOOTS_FINISH, BELT_FINISH],
                                              {BOOTS: [33.1, 0.9, 7.6], "rubber_dark": [20.0, 0.0, 0.0]}),
}

WATER_TANK_CLOSE_UP = {"painted_panel": [80.3, -0.2, 6.0], "bare_steel": [67.3, -0.3, 1.0],
                       "tank_water": [53.2, -3.2, -2.3]}  # the finish-map method's measures, greenhouse, 2026-10-12
# The water tank's surfaces as the greenhouse's library gave them when it was fixed (2026-10-12), L*a*b*: the
# check's measured case, kept as numbers since every old material was retired (2026-10-21).
TANK_SURFACES = {"bare_steel": [66.3, -1.1, -4.5], "tank_water": [41.5, -3.2, -6.9], "cream_paint": [79.2, -0.7, 7.6]}
GREY_PANEL = [61.6, -1.5, -6.5]
# the engine room's core (2026-11-13): its glow, a `glowing` variant whose family the scene library coined ("energy"),
# baked its blue against the close-up's white-hot column; its opaque casing off its close-up too
CORE_GLOW = route_settings.settings_name("core_glow", {"token": "reactor-blue", "roughness": 0.2, "metal": 0.0})


def core_record():
    core = baked_record({CORE_GLOW: (0.23, [63.7, 7.0, -56.4]), "casing": (0.77, [32.3, 0.1, -2.6])},
                        {CORE_GLOW: [77.1, 0.7, -2.7], "casing": [70.0, 0.0, 0.0]})
    core["surfaces"][CORE_GLOW]["family"] = "energy"
    return core


def fragment_record(degrees):
    """The wreck's grey fragment: three near-neutral surfaces baked within 4.5 L*, its close-up 38.5 L* apart."""
    return baked_record({"bare_steel": (0.4118, [64.1, -0.8, -3.2]), "galvanized_steel": (0.4758, [68.6, -1.2, -2.2]),
                         "roof_steel_paint": (0.1123, [63.7, -1.0, -2.7])},
                        {"bare_steel": [51.1, 1.9, 7.0], "galvanized_steel": [89.6, -0.2, 3.6],
                         "roof_steel_paint": [49.7, -1.0, 2.8]}, degrees)


# Each checked model (its name in checks.json) -> (its record, the faults the bake check names on it: one tuple of the
# words each fault holds, in order).
JUDGED = {
    # the seed tray's label border straddles the black plastic: a clean border passes, a smudge along it fails
    "seed_tray_clean": (lambda: paper_record(SEED_TRAY_PAPER), []),
    "seed_tray_smudged": (lambda: paper_record(smudged(SEED_TRAY_PAPER)), [("printed_paper", "near black")]),
    # a surface's own drawn seams are its colours, not blotches; without its second colour they are
    "quilt_seamed": (lambda: quilt_record(QUILT_COTTON), []),
    "quilt_without_its_seams": (lambda: quilt_record({"colour": QUILT_COTTON["colour"]}), [("near black",)]),
    # a covering dome is judged by its own colour, so the close-up holds nothing to compare; uncovered it is compared
    "beacon_covered": (lambda: baked_record({"red_plastic": (1.0, [38.5, 57.0, 47.5])},
                                            labelled_close_up(CLOSE_UPS["a covering dome"][0])), []),
    "beacon_uncovered": (lambda: baked_record({"red_plastic": (1.0, [38.5, 57.0, 47.5])},
                                              labelled_close_up(CLOSE_UPS["an uncovered dome"][0])),
                         [("red_plastic", "its close-up")]),
    # a glowing variant counted lit (check_seen, as the row judges it) is judged by its own colour, its casing still
    # compared; unlit, both are off their close-up
    "core_unlit": (core_record, [(CORE_GLOW, "its close-up"), ("casing", "its close-up")]),
    "core_lit": (lambda: check_seen.lit_as_light(core_record(), {"core_glow"}), [("casing", "its close-up")]),
    # boots keyed as the part bakes: baked L* 65.5 against their close-up's 33 fails
    "body": (lambda: baked_record({BOOTS: (1.0, [65.5, 0.0, 0.0])},
                                  labelled_close_up(CLOSE_UPS["boots by their settings, a belt moved"][0])),
             [(BOOTS, "33.3")]),
    # the water tank as stored (1.4 m wide, 3.3 m from the greenhouse's nearest view): its paint baked darker than its
    # steel; its water 8.9 b* off its paint is 1.9 noticeable differences at that size, told apart, not one look
    "water_tank_stored": (lambda: baked_record({"painted_panel": (0.7253, GREY_PANEL),
                                                "bare_steel": (0.1536, [66.3, -1.1, -4.5]),
                                                "tank_water": (0.1212, [58.7, -1.7, 2.4])}, WATER_TANK_CLOSE_UP, 23.83),
                          [("painted_panel is 13.0 L* lighter than bare_steel",)]),
    "water_tank_grey_body": (lambda: baked_record({"painted_panel": (0.7253, GREY_PANEL),
                                                   "bare_steel": (0.1536, TANK_SURFACES["bare_steel"]),
                                                   "tank_water": (0.1212, TANK_SURFACES["tank_water"])},
                                                  WATER_TANK_CLOSE_UP, 23.83),
                             [("lighter than bare_steel",)]),
    "water_tank_cream": (lambda: baked_record({"cream_paint": (0.7253, TANK_SURFACES["cream_paint"]),
                                               "bare_steel": (0.1536, TANK_SURFACES["bare_steel"]),
                                               "tank_water": (0.1212, TANK_SURFACES["tank_water"])},
                                              {"cream_paint": WATER_TANK_CLOSE_UP["painted_panel"],
                                               **{name: WATER_TANK_CLOSE_UP[name]
                                                  for name in ("bare_steel", "tank_water")}}, 23.83), []),
    # one surface is one look by design; a dark part 50 L* off its close-up is over 32
    "panel_1": (lambda: baked_record({"painted_panel": (1.0, GREY_PANEL)}, {"painted_panel": [80.3, -0.2, 6.0]}), []),
    "cabinet_1": (lambda: baked_record({"painted_panel": (0.9, GREY_PANEL), "rubber": (0.1, [9.3, 0.5, -1.4])},
                                       {"painted_panel": [61.0, 0.0, 0.0], "rubber": [62.0, 0.0, 0.0]}),
                  [("rubber", "over 32")]),
    # one look fails only what a viewer cannot tell apart at the place's view distance: the wreck's access cover,
    # 4.5 m from wreck-home, is 9.3 L* apart at 6 degrees and seen; the fragment is one grey look; with no view
    # distance it is named, never passed
    "access_cover": (lambda: baked_record({"bare_steel": (0.2813, [66.3, -1.1, -4.5]),
                                           "hull_white_scorched": (0.7187, [75.6, -1.2, -1.0])},
                                          {"hull_white_scorched": [92.7, -0.3, 0.0], "bare_steel": [65.4, 1.6, 5.6]},
                                          11.29), []),
    "fragment_seen": (lambda: fragment_record(4.71), [("one grey look",)]),
    "fragment_unplaced": (lambda: fragment_record(None), [("no view distance",)]),
}



def refused(code):
    """An HTTP refusal Google answers with `code`."""
    return urllib.error.HTTPError("url", code, "refused", {}, io.BytesIO())


# finish_ask.generated over the faults Google answers in turn before "answered": (case, the faults, what reaches the
# row (None for the answer), the asks made); `room` is called before every one
GENERATED = [
    ("a timeout reaches the row at once", (TimeoutError("The read operation timed out"),), TimeoutError, 1),
    ("rate and full service refusals are asked again", (refused(429), refused(503)), None, 3),
    ("failing and gateway refusals are asked again (audit, 2026-10-22: these stopped the row)",
     (refused(500), refused(504)), None, 3),
    ("a bad request reaches the row asked once", (refused(400),), urllib.error.HTTPError, 1),
    ("refused every time is no answer", (refused(429), refused(503), refused(429)), finish_ask.NoAnswer,
     finish_ask.REFUSED_ASKS),
    ("a lost connection is no answer", (urllib.error.URLError(ConnectionRefusedError(111, "refused")),),
     finish_ask.NoAnswer, 1),
]


def answered(text):
    """A Gemini response whose one part is `text`."""
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}


# route_ask.asked over one batch of bodies ({"ask": name}) outside a cleared run, the cache holding `cached`'s
# responses: (case, cached, the bodies asked, what it answers (an exception raised, or {name: text, or the Unanswered
# class}), the bodies whose answer stays cached, the keys google_batch was sent)
ASKED = [
    ("an uncached ask outside a cleared run is refused before any batch is sent", {"cached": answered("{}")},
     ("cached", "uncached"), compute.Refused, {"cached"}, []),
    ("a batch the cache answers whole runs with no clearance and no key (fault, 2026-10-29: body-face-earth refused "
     "in a free-only run although the cache held its answer)", {"cached": answered("{}")}, ("cached",),
     {"cached": "{}"}, {"cached"}, [None]),
    ("an answer that does not parse is a gap dropped from the cache (fault, 2026-10-25, surface-library@camp: a "
     "malformed answer kept, every later try read it back)",
     {"broken": answered('{"surfaces": [{,}]}'), "good": answered('{"surfaces": []}')}, ("broken", "good"),
     {"broken": route_ask.google_batch.Unanswered, "good": '{"surfaces": []}'}, {"good"}, [None]),
]

# route_recheck.finish_lines on a glass-brown finish of suit_patches (red by default): (case, its settings, words its
# line holds, words it lacks); astronaut-made-s1 (2026-10-22): glass-brown patches were worded red
WORDED = [
    ("a finish worded in the token it is drawn and baked in", {"token": "glass-brown", "roughness": 0.9, "metal": 0.0},
     ("roughness 0.90",), ("drawn red",)),
    ("a finish with no settings worded in its surface's colour", None, ("drawn red",), ()),
]


def test_every_part_takes_a_library_surface_and_is_held_to_it(monkeypatch):
    """Every baked part is held to its library surface and its take's close-up: the finishes' labels give the
    close-up colours, the bake check's gate (check_seen.judge_lit, the surfaces-check row's) judges one checks.json of
    every case and names exactly the faults each model's row expects, and the view distance it judges one look at is
    read from the place's scene record and kit. A surface proposed to the library stands as the first proposed of its
    name, whatever its case; a take's short feet are levelled in the resting check's band. A bake lies on its surface
    dirtied only as far as its place's dirt and worn only toward its bare colour as far as its place's wear, its colour
    each channel's area median; the paint's labels become parts (unvoted faces walked, loose bits and crumbs merged, no
    finish cleaned away whole, agreement counted against the maps, a finish out of order found by its own colour); a
    place nobody walks bakes with no kicks, and bake and paint each rent one machine class. A listed finish is held
    to its colour (its family's nearest surface or the room's kit surface only where the list's meaning, recipe, glow
    and hue, is kept; as the parts row makes it a pick and a nearer listed surface stay), kept in its close-up's
    lightness order, judged by the list's meaning gate, and a light built in code takes its glowing surface; the
    parts row makes through the picks row and a list's reply is parsed to library names. The library a part takes
    from is the scene's own: its palette read by one ask over its locked concept (or a line's every concept and
    close-up), its surfaces made fresh from that palette by one ask covering every take's kind, ground row and shell
    kind with no recipe that paints a picture, and the repository's library the method alone, its empty reads named. Every body
    that does not shine has a paid face row by the concept in force (today's when none is locked), its face made from
    one Gemini ask in the method's recipes and held to its palette and method, no face where no answer comes or the
    setting lacks its physics; the four finish-route asks go to Claude, a refused palette answer asked once more.
    The paint takes the method's surface and records a part's proposal; a gate that cannot read its evidence answers
    unknown. The surface line is rows of world one, each take painted by one place and every claim baked by its place;
    a place without data blocks before anything is spent, one with nothing to paint has no rows, and a method change
    moves only the rows that read the library. A take that stands on the floor by its rows (its own place's, the
    claiming place's, a designed place's hand-in) has its short legs, its sloping base and its resting face brought
    level before its bake, a leg past the band refused and judged a missing leg, and its baked model held to stand.
    The list asks every take in one batch (a lost answer a gap the list names), and once more a take whose answer
    lists a finish it labels no region with; the split gives each face one finish by the labels alone, the one the
    views that see it most squarely give, unassigned area over its tolerance a gap; a small colour far from the rest
    keeps a region of its own; and a finish is held against its close-up's colour, never the light-baked texture.
    The paint and bake rows key the library by part (a variant added anywhere moves every bake, a kind's details the
    paint); an accepted output carries only from a committed tree, its code change proved a no-op file by changed
    file at the code its commit had, or over earlier outputs that hand its row the same content by its content rule.
    A rolled take is stood square before it is laid, unless one guard list (by row kind, anchor and words) or its
    code keeps the pose it was made in, or its Pixal3D close-up outlines its made pose better; the bake measures each
    copy again as baked and undoes a turn that cannot square it; `stands square` fails a tumbled bake by name with
    its angle and leaves a kept one out; the bake's outline is the likeness gate's."""
    for case, parts, stands in PROPOSED:  # the paint takes each part's method surface, its proposal to the registry
        store = a_store()
        found = surfaces.place_line.method_surfaces("power_unit-r3", "old_station", [
            {"part": index, "judge": judge, "proposed": proposal} for index, (judge, proposal) in enumerate(parts)],
            registry.Registry(store))
        entries = {registry.entry_id(entry["name"]): entry for entry in store.registry("surfaces")}
        assert [record["surface"] for record in found] == [judge for judge, _ in parts], (case, found)
        assert len(entries) == len({first for first in stands if first is not None}), (case, entries)
        for index, first in enumerate(stands):
            if first is None:
                assert found[index]["proposed"] is None, (case, index)
                continue
            judge, proposal = parts[first]
            spec = {**proposal, "status": "proposed", "stands_in": judge}
            entry = entries[registry.entry_id(parts[index][1]["name"])]
            assert found[index]["proposed"] == spec, (case, index, found[index])
            assert (entry["name"], entry["spec"], entry["first"]["part"]) == (proposal["name"], spec, first), (
                case, index, entry)
    for case, (finishes, close_up) in CLOSE_UPS.items():
        assert labelled_close_up(finishes) == close_up, case
    # the surfaces-check row's gate as check_seen.lit_gates sets it, judged before and after its checks.json is written
    gate = surface_gates.guarded("baked matches its surfaces", check_seen.judge_lit)
    with tempfile.TemporaryDirectory() as scratch:
        unread = checks.judge(gate, scratch, {}, None)  # a gate that cannot read its evidence answers unknown
        assert unread.answer == checks.UNKNOWN and "checks.json" in unread.reason, unread
        records = {model: dict(make(), missing_maps=[]) for model, (make, _) in JUDGED.items()}
        (pathlib.Path(scratch) / "checks.json").write_text(json.dumps(records))
        found = checks.judge(gate, scratch, {}, None)  # a row that reads no scene library counts nothing lit
    expected = sum(len(faults) for _, faults in JUDGED.values())
    assert found.answer == checks.FAIL and found.reason == f"{expected} of {len(JUDGED)} faults over the models", found
    for model, (_, faults) in JUDGED.items():
        named = [fault for fault in found.findings if fault.startswith(f"{model}: ")]
        assert len(named) == len(faults) and all(all(word in fault for word in words)
                                                 for fault, words in zip(named, faults)), (model, named)
    # the table wraps the make (stages/gaps.py: an accepted gap moves a fault, the wrapper unwraps to the judge); the
    # finish route's check is bake_check's against the bake's specs (route_check.py), through check_seen.py
    assert inspect.unwrap(ROWS["surfaces-check"].make) is check_seen.make_check
    assert abs(bake_check.noticed([50, 0, 0], [55.155, 0, 0], 10.0) - 1.0) < 0.01, "ND(50) of L* at 6 degrees"
    # route_check holds each surface against the spec the bake baked, the library's own surfaces kept, at the scene
    # palette's wear, dirt and dirt colour (nothing of place.json's); a surface with its own wear is measured at it,
    # the others at the place's
    seen = {}
    with tempfile.TemporaryDirectory() as temporary, pytest.MonkeyPatch.context() as held:
        bake = pathlib.Path(temporary)
        (bake / "specs.json").write_text(json.dumps({"painted_panel__sign_red_r100_m000": {"colour": [1, 0, 0]}}))
        for name in ("by_library", "resolved", "wear_of"):  # the check sets these for the scene; put back after
            held.setattr(library, name, getattr(library, name))
        held.setattr(route_check.bake_check, "check_model", route_check.bake_check.check_model)
        held.setattr(route_check.bake_check, "check_step", lambda inputs, out: seen.update(
            library=library.by_library("cockpit"), resolved=library.resolved("cockpit"), wear=library.wear_of("cockpit")))
        route_check.check_step({"bake": bake, "finish-route-palette": paletted(bake),
                                "surface-library": libraried(bake)}, bake)
    assert seen["library"]["painted_panel__sign_red_r100_m000"] == {"colour": [1, 0, 0]}, seen["library"]
    assert "painted_panel" in seen["library"] and seen["wear"] == (0.4, 0.3) and seen["resolved"] == {}, seen
    assert seen["library"]["painted_panel"]["dirt_colour"] == library.token_colours({"tokens": TOKENS})["regolith"]
    checked = route_check.own_wear_checked(
        lambda name, entry, labelled, made, materials, dirt=0.0, wear=0.0: {
            "surfaces": {surface: {"wear": wear} for surface in materials}})(
        "m", {}, None, None, {"a": {}, "b": {"wear": 0.8}}, 0.2, 0.4)
    assert checked["surfaces"] == {"a": {"wear": 0.4}, "b": {"wear": 0.8}}, checked
    desk = [{"model": "models/hub_kit/comms_1.gltf", "at": [2.0, 0.0, 0.0], "yaw": 90.0,
             "children": [{"model": "models/hub_kit/headset_1.gltf", "at": [1.0, 0.5, 0.0]}]}]
    spots = list(bake_check.object_spots(desk, {"headset_1": {"size": [0.2, 0.2, 0.1]}}))
    assert [model for model, _, _ in spots] == ["headset_1"], "a model laid on a desk the kit does not size is found"
    assert [round(value, 6) for value in spots[0][1]] == [2.0, 0.5, -1.0], spots  # turned by the desk's yaw
    # no kit (retired 2026-10-21): a ship place's kit laid from its scene record's objects, sized by their bakes
    record = {"views": [{"eye": [0.0, 1.6, 0.0]}], "objects": [
        {"name": "sliding_door_1", "bake": "sliding_door_1", "at": [0.0, 1.6, 2.0]},
        {"name": "sliding_door_2", "bake": "sliding_door_1", "at": [0.0, 1.6, 4.0]},
        {"name": "vault_door_1", "bake": "vault_door_1", "at": [0.0, 0.0, 1.0]}]}
    with tempfile.TemporaryDirectory() as temporary:
        scene, laid = pathlib.Path(temporary) / "record.json", pathlib.Path(temporary) / "kit.json"
        scene.write_text(json.dumps(record))
        for baked, degrees in (({"sliding_door_1": {"size": [1.0, 2.0, 0.2]}}, {"sliding_door_1": 28.07}),
                               ({}, {})):  # its 1.0 m middle side, 2 m from the eye; unbaked: no size, no distance
            laid.write_text(json.dumps(check_seen.laid_kit(record, baked)))
            assert bake_check.seen_degrees({"scene record": scene, "kit": laid}) == degrees, baked
    for case, baked, clean, dirt_colour, dirt, bare, wear, side, bound in ON_SURFACE:
        distance = bake_check.on_surface(np.array(baked), np.array(clean), None if dirt_colour is None else
                                         np.array(dirt_colour), dirt, None if bare is None else np.array(bare), wear)
        assert (distance < bound) if side == "<" else (distance > bound), (case, distance)
    order = np.argsort(JUNCTION_BOX[:, 0])  # the old pick, the triangle at the area's median L*, was a grey one
    assert JUNCTION_BOX[order][np.searchsorted(np.cumsum(np.ones(100)), 50.0)].tolist() == GREY
    for case, areas, middle in AREA_MEDIANS:
        assert bake_check.area_median(JUNCTION_BOX, areas).tolist() == middle, case
    # the paint's labels made parts, on one sphere: its top two quarters voted 0 and 1, single faces of finish 1 dotted
    # over it, and a map saying finish 1 on its front half
    sphere = trimesh.creation.icosphere(subdivisions=4)
    middles = sphere.triangles_center
    seen = np.full(len(sphere.faces), -1)
    seen[(middles[:, 2] > 0.5) & (middles[:, 0] > 0)], seen[(middles[:, 2] > 0.5) & (middles[:, 0] <= 0)] = 0, 1
    dots = np.flatnonzero((middles[:, 1] > 0.9) | (middles[:, 0] > 0.97))[::3]
    dotted = np.zeros(len(sphere.faces), dtype=int)
    dotted[dots] = 1
    front = np.where(middles[:, 1] > 0, 1, 0)
    walked, without = finish_parts.walked(sphere, seen), finish_parts.cleaned(sphere, dotted, 2)
    agreement = finish_parts.agreement(sphere, without, {"front": front})
    back = middles[:, 2] < -0.5  # unvoted faces take the nearest voted label along the surface
    assert (walked >= 0).all() and (walked[back & (middles[:, 0] > 0.3)] == 0).mean() > 0.9, "the back takes 0 by x"
    assert (walked[back & (middles[:, 0] < -0.3)] == 1).mean() > 0.9, "the back takes 1 by -x"
    assert (without[dots] == 1).all() and (without[dotted == 0] == 0).mean() > 0.99, "a finish cleaned away whole"
    assert 0.4 < agreement["front"] < 0.6, agreement  # the paint's finish 1 is only dots: about half the map agrees
    crumbs = [trimesh.creation.box(extents=extents).apply_translation(centre) for extents, centre, _ in CRUMBS]
    total = trimesh.util.concatenate([trimesh.creation.box(extents=HOST[0]), *crumbs]).area
    assert all(crumb.area / total < finish_parts.ISLAND_LEAST for crumb in crumbs), "each stripe a crumb"
    assert sum(crumb.area for crumb in crumbs) / total >= finish_parts.ISLAND_LEAST, "together over ISLAND_LEAST"
    for case, pieces, parts, joined in MERGED:
        boxes = [trimesh.creation.box(extents=extents).apply_translation(centre) for extents, centre, _ in pieces]
        label = np.concatenate([np.full(len(box.faces), finish) for box, (_, _, finish) in zip(boxes, pieces)])
        part_of, merged = finish_parts.merged_islands(trimesh.util.concatenate(boxes), label)
        piece_of = np.repeat(np.arange(len(boxes)), [len(box.faces) for box in boxes])
        held = np.isin(piece_of, joined)
        assert len(np.unique(part_of)) == parts and len(np.unique(part_of[held])) == 1, (case, part_of)
        assert (merged[held] == 1).all(), (case, merged)
    for case, before, after, areas, kept in KEPT:
        assert finish_parts.kept_finishes(np.array(before), np.array(after), np.array(areas)).tolist() == kept, case
    # patchy paint on that sphere and a loose 5 cm box 3 m off it, each row's finishes laid by mark
    shape = trimesh.util.concatenate([sphere, trimesh.creation.box(extents=(0.05,) * 3).apply_translation((3, 0, 0))])
    centres, on_sphere = shape.triangles_center, np.arange(len(shape.faces)) < len(sphere.faces)

    def near(spot, reach):
        return on_sphere & (np.linalg.norm(centres - spot, axis=1) < reach)

    def share(mask):
        return shape.area_faces[mask].sum() / shape.area

    def marking(rows, under=None):
        found = np.zeros(len(shape.faces), dtype=int) if under is None else under.copy()
        for mark, finish in rows:
            found[marks[mark]] = finish
        return found

    marks = {"under": on_sphere & (centres[:, 2] < -0.5), "patch": near((0, 0.99, 0.1), 0.08),
             "lone": near((0.99, 0, 0.1), 0.08), "loose": ~on_sphere, "piece": ~on_sphere & (centres[:, 0] > 3.02),
             "crumb": near((0, 0, 1), 0.06), "blotches": np.zeros(len(shape.faces), dtype=bool),
             "specks": np.zeros(len(shape.faces), dtype=bool), "screens": np.zeros(len(shape.faces), dtype=bool)}
    plain = marking(LAID_BASE) == 0
    spots = []  # sphere points apart, so no two specks join into one island
    for spot in sphere.vertices[::40]:
        spots += [spot] if all(np.linalg.norm(spot - other) > 0.2 for other in spots) else []
    for spot in spots[:30]:
        marks["specks"] |= near(spot, 0.06) & plain
    for spot in ((-0.7, 0.7, 0.1), (0.7, 0.7, -0.1), (-0.7, -0.7, 0.1), (0.7, -0.7, -0.1)):
        marks["screens"] |= near(np.array(spot) / np.linalg.norm(spot), 0.12)
    for spot in ((0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
        marks["blotches"] |= near(spot, 0.18)
    marks["portholes"] = plain & (near((0, -0.99, 0.1), 0.05) | near((-0.99, 0, 0.1), 0.05))
    speck_of = patchy.islands(marking(LAID_BASE + [("specks", 2)]), shape.face_adjacency)
    screen_of = patchy.islands(marking(STRAYS[2][1]), shape.face_adjacency)
    marks["apart"] = marks["specks"] & ~np.isin(screen_of, screen_of[marks["screens"]])
    screens = [share(screen_of == screen) for screen in np.unique(screen_of[marks["screens"]])]
    assert 0 < share(marks["patch"]) < patchy.STRAY_ISLAND and share(marks["portholes"]) < patchy.STRAY_ISLAND
    assert len(np.unique(speck_of[marks["specks"]])) > 10 and share(marks["specks"]) > patchy.STRAY_ISLAND
    assert all(share(speck_of == speck) < finish_parts.ISLAND_LEAST for speck in np.unique(speck_of[marks["specks"]]))
    assert len(screens) == 4 and all(finish_parts.ISLAND_LEAST <= each < patchy.STRAY_ISLAND for each in screens)
    assert marks["apart"].any(), "a speck no screen's island holds"
    for case, rows, held, gone, moved, largest, stray in STRAYS:
        before = marking(rows)
        found = finish_parts.without_strays(shape, before)
        assert all((found[marks[mark]] == finish).all() for mark, finish in held), case
        assert not any((found[marks[mark]] == finish).any() for mark, finish in gone), case
        assert moved is None or (found[~marks[moved]] == before[~marks[moved]]).all(), case
        if largest is not None:
            finish, mark = largest
            left = np.unique(patchy.islands(found, shape.face_adjacency)[found == finish])
            assert len(left) == 1 and (found == finish).sum() < marks[mark].sum(), (case, len(left))
        judged = [finish_parts.patchiness(shape, labels, labels, [BODY_PAINT] * 3) for labels in (before, found)]
        assert stray is None or judged[1]["pass"], (case, judged)
        assert stray != "drops" or judged[1]["stray"] < judged[0]["stray"], (case, judged)
    kept, alone = finish_parts.without_strays(shape, marking(STRAYS[2][1])), None
    for case, rows, held, most, stray in PARTED:
        part_of, finish_of = finish_parts.merged_islands(shape, marking(rows, kept))
        judged = finish_parts.patchiness(shape, finish_of, part_of, [BODY_PAINT] * 3)
        alone = judged["stray"] if alone is None else alone
        holding = np.any([marks[mark] for mark in held], axis=0) if held else None
        assert holding is None or len(np.unique(part_of[holding])) <= most, (case, part_of)
        assert {"passes": judged["pass"], "as alone": judged["stray"] == alone,
                "under a screen": 0 < judged["stray"] < min(screens)}[stray], (case, judged, screens)
    blotched = marking([("blotches", 1)])
    for case, finishes, parts, passes in BLOTCHES:
        part_of = blotched if parts == "of their own" else np.zeros(len(shape.faces), dtype=int)
        judged = finish_parts.patchiness(shape, blotched, part_of, finishes)
        assert finish_parts.detail_finish(finishes[1]) == passes and judged["pass"] == passes, (case, judged)
        assert passes or (judged["stray"] > 0.03 and route_split.patchy_fault(judged).startswith("patchy paint: stray"))
    lightness = finish_parts.opaque_lightness(GREYS)
    for case, lighter, other, out in OUT_OF_ORDER:
        assert bool(finish_parts.out_of_order(lighter, other, GREYS, lightness)) == out, case
    for case, finish, through in SEE_THROUGH:
        assert finish_parts.see_through(finish, SURFACE_FAMILIES) == through, case
    for case, data, kicks in UNWALKED:
        painted = place_line.unwalked(SPECS, data)
        assert (painted is SPECS) if kicks is None else ({spec["kicks"] for spec in painted.values()} == kicks), case
    for name in RENTED:
        assert "," not in getattr(place_line, name), (name, "rents more than one machine class")
    checked = {}
    for case, take, finishes, measured, surfaces_of, kit, held, expected in CHECKED:
        with parts_kept.held() if held else contextlib.nullcontext():
            found = finish_parts.checked_finishes(take, copy.deepcopy(finishes), measured, surfaces_of,
                                                  *([] if kit is None else [kit]))
        checked[case] = found
        assert unlike(found, finishes, expected) == [], (case, found)
    for case, thing, finishes, surfaces_of, expected in IN_ORDER:
        found = finish_parts.in_close_up_order({"object": thing}, copy.deepcopy(finishes), surfaces_of)
        assert unlike(found, finishes, expected) == [], (case, found)
    plate = checked["as the row makes it, brushed steel seen as the deck plate still takes it"][0]
    cables = {"object": "thick red cables", "parts": CABLE_PARTS, "finishes": finish_parts.looked(
        [dict(HANDRAIL, surface="deck_grate", listed_surface="bare_steel", by="the room's kit surface by colour"),
         dict(plate, listed_surface="bare_steel")], STEELWORK)}
    with tempfile.TemporaryDirectory() as scratch:
        for case, take, made, expected in MEANING:
            record = made(cables)
            faults = finish_parts.meaning_faults(take, record)
            assert len(faults) == len(expected) and all(all(word in fault for word in words)
                                                        for fault, words in zip(faults, expected)), (case, faults)
            (pathlib.Path(scratch) / "parts.json").write_text(json.dumps({"takes": {take: record}}))
            verdict = route_parts.judge_meaning(pathlib.Path(scratch), {}, None)
            assert verdict.answer == (checks.FAIL if expected else checks.PASS), (case, verdict)
    assert "kept the list's meaning" in [check.name for check in ROWS["surfaces-parts"].checks]
    with tempfile.TemporaryDirectory() as scratch:
        mark = pathlib.Path(scratch) / "code.json"
        for case, take, size, lit in LIT_TAKES:
            mark.write_text(json.dumps({"route": "code", "size": size}))
            assert bool(route_parts.lit_take(take, mark)) == lit, case
    for case, finishes, surfaces_of, held, expected in LIT:
        with parts_kept.held() if held else contextlib.nullcontext():
            found = route_parts.lit_finishes(copy.deepcopy(finishes), surfaces_of)
        assert unlike(found, finishes, expected) == [], (case, found)
    # every place's surface line is rows of world one, each a place's, every paid one priced, waiting on what it reads
    # (an exact set where the row's waits are all named): the scene's surfaces made fresh from its palette before
    # anything is listed (owner, 2026-10-21); the parts row made through recheck_picks.make_parts (parts_kept.make_parts
    # on the picked list) from the free picks row that selects just before it; the bake painting the method's interface
    # at the scene palette's wear and dirt; the paint reading the bake's painted takes
    # (the route the default line, its paid rows the palette, library, list, bake and recheck, none reading
    # data/definitions/place.json: a scene's palette comes from its design)
    names = [row.name for row in stages.STAGES]
    assert [stage.name for stage in surfaces.ROWS] == [
        "finish-route-palette", "surface-library", "finish-route-views", "finish-route-list", "finish-route-split",
        "surfaces-parts", "surfaces-bake", "surfaces-paint", "finish-route-recheck", "surfaces-check"] and all(
        stage.name in ROWS and stage.grain == "place" and (stage.euros or not stage.paid) for stage in surfaces.ROWS)
    assert [stage.name for stage in surfaces.ROWS if stage.paid] == [
        "finish-route-palette", "surface-library", "finish-route-list", "surfaces-bake", "finish-route-recheck"]
    assert not [stage.name for stage in surfaces.ROWS
                if "places" in (stage.files("cockpit") if callable(stage.files) else stage.files)]
    for row, waits, exactly in (
            ("surface-library", {"finish-route-palette"}, True),
            ("finish-route-list", {"finish-route-palette", "surface-library"}, False),
            ("surfaces-parts", {"finish-route-palette", "surface-library", recheck_picks.ROW}, False),
            ("finish-route-recheck", {"finish-route-palette", "surface-library"}, False),
            ("surfaces-check", {"finish-route-palette", "surface-library"}, False),
            ("surfaces-bake", {"finish-route-palette", "surface-library", "surfaces-parts"}, True),
            ("surfaces-paint", {"surfaces-bake"}, True)):
        assert (set(ROWS[row].after) == waits) if exactly else (waits <= set(ROWS[row].after)), (row, ROWS[row].after)
    assert inspect.unwrap(ROWS["surfaces-parts"].make) is recheck_picks.make_parts, ROWS["surfaces-parts"].make
    assert names.index(recheck_picks.ROW) == names.index("surfaces-parts") - 1, names
    assert recheck_picks.parts_kept is parts_kept
    assert not ROWS[recheck_picks.ROW].paid and ROWS[recheck_picks.ROW].selects
    # one world's line over three places: the greenhouse paints a crop crate (its own data, the old greenhouse's
    # retired), the tube lists nothing (code-built pieces only) and has no rows, and nowhere has no data, so it
    # blocks at its first row and its bake before anything is spent. A method change (a recipe's new default) moves
    # only the rows that read the library: the scene's surfaces, the list, parts, paint, bake, recheck and check, never
    # the views and split (the split reads the list's answers: identical answers keep its key, the graph's own test);
    # the palette row reads the wear levels alone
    data, home = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    for folder in ("library", "definitions"):
        shutil.copytree(REPO / "data" / folder, data / folder)
    (data / "surfaces").mkdir()
    (data / "kit").mkdir()
    for place in ("greenhouse", "tube"):  # world one's places, each with its kit
        (data / "kit" / f"{place}.json").write_text("[]")
    (data / "surfaces/greenhouse.json").write_text(json.dumps({"place": "greenhouse", "library": "greenhouse", "takes": {
        "crate-t1": {"place": "greenhouse", "kind": "crate", "object": "a crop crate", "library_places": []}},
        "bake": {"models": {"crate_1": "crate-t1"}}}))
    (data / "surfaces/tube.json").write_text(json.dumps({"place": "tube", "takes": {},
                                                         "nothing": "code-built pieces only"}))
    kept_folder = surfaces.data.FOLDER
    try:
        # the repository's surface data and world one's alike: each take painted by one place, every place listing
        # takes or saying why not (and painting exactly when it lists some), every model claimed elsewhere painted and
        # baked by its place
        for folder in (kept_folder, data / "surfaces"):
            surfaces.data.FOLDER, owner = folder, {}
            placed = {path.stem: json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))}
            for place, record in placed.items():
                assert (folder.parent / "kit" / f"{place}.json").exists() or shapes_first.no_place(place), (
                    f"{place}: no such place")
                assert record["takes"] or record.get("nothing"), f"{place}: lists nothing to paint and says not why"
                assert surfaces.data.paints(place) == bool(record["takes"]), place  # the rows' own module
                for take, entry in record["takes"].items():
                    assert take not in owner, f"{take}: painted by {owner.get(take)} and {place}"
                    owner[take] = place
                    assert {"place", "kind", "object", "library_places"} <= set(entry), f"{place} {take}"
                assert not record.get("bake") or set(record["bake"]["models"].values()) <= set(record["takes"]), (
                    f"{place}: bakes a take it does not paint")
                for model, claim in record.get("elsewhere", {}).items():
                    other = placed[claim["place"]]
                    assert claim["take"] in other["takes"], (
                        f"{place} {model}: {claim['place']} does not paint {claim['take']}")
                    assert claim["take"] in other["bake"]["models"].values(), (
                        f"{place} {model}: {claim['place']} bakes none")
        world = graph.Environment("world1", 1, {"data": str(data), "home": str(home), "repo": str(REPO),
                                                "seeds": str(home)})
        runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
        assert "its input surfaces is missing" in runner.node_status(runner.stages["finish-route-views"], "nowhere")
        assert not any(node.endswith("@tube") for node in runner.status(["tube"]))
        with pytest.raises(graph.Blocked) as blocked:
            runner.file_keys(runner.stages["surfaces-bake"], "nowhere")
        assert "nowhere.json" in str(blocked.value), blocked.value
        for stage in surfaces.ROWS:  # each file a row names, written small in the world's own home
            for name in runner.files_of(stage, "greenhouse"):
                path = runner.file_path(stage, name, "greenhouse")
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(name)
        before = {stage.name: runner.file_keys(stage, "greenhouse") for stage in surfaces.ROWS}
        materials = json.loads((data / "library" / "materials.json").read_text())
        materials["recipes"]["rubber"]["roughness"] = 0.8
        (data / "library" / "materials.json").write_text(json.dumps(materials))
        moved = {stage.name for stage in surfaces.ROWS if runner.file_keys(stage, "greenhouse") != before[stage.name]}
        assert moved == {"surface-library", "finish-route-list", "surfaces-parts", "surfaces-paint", "surfaces-bake",
                         "finish-route-recheck", "surfaces-check"}, moved
        materials["wear_levels"]["scarred"] = 1.0
        (data / "library" / "materials.json").write_text(json.dumps(materials))
        assert runner.file_keys(runner.stages["finish-route-palette"], "greenhouse") != before["finish-route-palette"]
        # the object filter keys only a selecting row: the views take it, sorted, and no take's model file; the paint
        # never
        views = runner.stages["finish-route-views"]
        assert runner.params_of(views) == {}, runner.params_of(views)
        runner.objects = frozenset({"b", "a"})
        assert runner.params_of(views) == {"objects": ["a", "b"]} and runner.params_of(
            runner.stages["surfaces-paint"]) == {}
        assert not any(name.startswith("model ") for name in runner.files_of(views, "greenhouse"))
    finally:
        surfaces.data.FOLDER = kept_folder
        shutil.rmtree(data)
        shutil.rmtree(home)
    # world one's default line runs the route at a place, and none of the rows it replaced
    line = [graph.node_name(*node) for node in graph.Runner(stages.STAGES, stages.world1(), a_store()).line_nodes(
        ["cockpit"], False)]
    assert all(f"{row.name}@cockpit" in line for row in surfaces.ROWS), line
    assert not [name for name in line if name.split("@")[0] in (
        "surfaces-inputs", "surfaces-turntable", "surfaces-lists", "surfaces-maps", "surfaces-names",
        "surfaces-segvigen", "finish-route-fill")], line
    reply = json.dumps({"finishes": [{"parts": "foil", "finish": "gold foil", "surface": "M1", "fits": True},
                                     {"parts": "legs", "finish": "steel", "surface": "M2", "fits": True}]})
    assert [entry["surface"] for entry in finish_ask.parsed_list(reply, {"mli_gold": {}, "bare_steel": {}})] == [
        "mli_gold", "bare_steel"], "a reply's codes are parsed to library names"
    with tempfile.TemporaryDirectory() as scratch:
        palettes = {}
        for index, (case, answer, where, judged, finding, has, lacks, pictures, kept, left_out) in enumerate(
                PALETTE_ASKS):
            (pathlib.Path(scratch) / f"palette-{index}").mkdir()
            out, verdict, asked = palette_asked(pathlib.Path(scratch) / f"palette-{index}", answer, **where)
            place = where.get("place", "cockpit")
            assert len(asked) == 1 and list(asked[0]) == [place], (case, asked)  # one ask a scene, in one batch
            parts = asked[0][place]["contents"][0]["parts"]
            assert sum("inline_data" in part for part in parts) == pictures == len(parts) - 1, (case, parts)
            text = parts[-1]["text"]
            assert all(word in text for word in has) and not any(word in text for word in lacks), (case, text)
            assert verdict.answer == judged and (finding is None or finding in verdict.findings[0]), (case, verdict)
            assert (out / "palette.json").exists() == (kept is not None), case
            made = json.loads((out / "palette.json").read_text()) if kept is not None else {}
            assert {field: made.get(field) for field in kept or {}} == (kept or {}), (case, made)
            assert not set(left_out) & set(made), (case, made)
            palettes[case] = out
        out = palettes[PALETTE_ASKS[0][0]]
        palette = json.loads((out / "palette.json").read_text())
        assert palette_library.wear(palette) == (0.8, 1.0) and scene_palette.palette_faults(out) == []
        with pytest.raises(library.LibraryEmpty) as empty:  # no surface exists until the surface-library row makes them
            palette_library.offered(palette)
        assert "run surface-library first" in str(empty.value), empty.value
        made = {}
        for index, (case, answer, on, judged, exact, within, pictured, has, lacks, enums) in enumerate(LIBRARY_ASKS):
            (pathlib.Path(scratch) / f"library-{index}").mkdir()
            out, verdict, asked = library_made(pathlib.Path(scratch) / f"library-{index}", answer, **on)
            assert len(asked) == 1 and list(asked[0]) == ["cockpit"], (case, asked)  # one ask a scene, in one batch
            body = asked[0]["cockpit"]
            text = body["contents"][0]["parts"][-1]["text"]
            assert all(word in text for word in has) and not any(word in text for word in lacks), (case, text)
            schema = body["generationConfig"]["responseSchema"]["properties"]["surfaces"]["items"]["properties"]
            for field, (offered, never) in enums.items():
                enum = set((schema[field].get("items") or schema[field])["enum"])
                assert set(offered) <= enum and not set(never) & enum, (case, field, enum)
            assert judged is None or verdict.answer == judged, (case, verdict)
            assert exact is None or tuple(verdict.findings) == exact, (case, verdict.findings)
            assert set(within) <= set(verdict.findings), (case, verdict.findings)
            assert pictured is None or [found for found in verdict.findings if "picture" in found] == pictured, \
                (case, verdict.findings)
            assert (out / "materials.json").exists() != isinstance(answer, Exception), case
            made[case] = out, verdict, body
        assert "none for it" in made[LIBRARY_ASKS[2][0]][1].findings[0], made[LIBRARY_ASKS[2][0]][1]
        out, verdict, body = made[LIBRARY_ASKS[0][0]]
        schema = body["generationConfig"]["responseSchema"]["properties"]["surfaces"]["items"]
        assert schema["properties"]["token"]["enum"] == list(PALETTE["tokens"]) and "colours" in schema["required"]
        # every surface answers a palette token for every colour setting, so no recipe's setting is left bare
        colours = schema["properties"]["colours"]
        assert colours["required"] == ["bare", "second"] == sorted(colours["properties"]), colours
        assert colours["properties"]["bare"]["enum"] == list(PALETTE["tokens"]), colours
        materials = json.loads((out / "materials.json").read_text())
        panel, window = materials["families"]["paint"]["variants"]["hull_panel"], \
            materials["families"]["glass"]["variants"]["window"]
        # its recipe's colour settings in its own tokens; a setting the recipe does not name is not taken
        assert panel["bare"] == "steel" and "second" not in panel and panel["token"] == "hull-trim", panel
        assert window["roughness"] == 1.0 and panel["seed"] != window["seed"], window  # held to 0 to 1
        assert materials["kinds"] == {"two_boxes": ["hull_panel"]} and materials["tokens"] == PALETTE["tokens"]
        assert materials["dirt"] == "regolith" and verdict.measures["surfaces"] == 2, (materials, verdict)
        assert materials["families"]["paint"]["surface"] == panel["surface"] == "steel_plate"  # the sound layer's
        # the rows after it read this library through the palette: the take's kind list, its specs in its tokens
        read = palette_library.read({"finish-route-palette": out.parent / "palette", "surface-library": out})
        assert set(palette_library.take_surfaces({"kind": "two_boxes"}, read)) == {"hull_panel", "window"}
        assert palette_library.specs(read)["hull_panel"]["bare"] == palette_library.library_tokens(read)["steel"]
        # the shell's parts find their surface in it (the earth seed, the scene record, the tiles)
        shell = json.loads((made[LIBRARY_ASKS[4][0]][0] / "materials.json").read_text())
        assert {part: palette_library.shell_surface(part, shell) for part in ("deck", "wall", "roof", "stair")} == {
            "deck": "panel", "wall": "panel", "roof": "panel", "stair": "panel"}
        marked = {"framed_photo": "framed photo" + scene_library.PICTURE_WORDS, "window_pane": "window pane"}
        # a library accepted before the marking is never failed by it
        for case in (LIBRARY_ASKS[6][0], LIBRARY_ASKS[7][0]):
            old = json.loads((made[case][0] / "materials.json").read_text())
            assert old.pop("picture_kinds") == ["framed_photo"], (case, old)
            sounds = {variant.get("surface") for family in old["families"].values()
                      for variant in family["variants"].values()}
            assert not [found for found in scene_library.library_findings(old, marked, sounds) if "picture" in found]
        palette = {"tokens": {}, "wear": {}, "library": str(pathlib.Path(scratch) / "shell.json")}
        (pathlib.Path(scratch) / "shell.json").write_text(json.dumps({"kinds": SHELL_KINDS}))
        assert palette_library.shell_surfaces(palette) == ["ceiling_panel", "deck_plate"]
        for part, surface in SHELL_PARTS:
            assert palette_library.shell_surface(part, {"kinds": SHELL_KINDS}) == surface, part
    assert palette_library.shell_surfaces({"tokens": {}, "wear": {}}) == []  # none while no library is read
    # an open place with a raised level: its level is the floor's kind; one with neither lays no shell
    level = {"w": 6.0, "d": 4.0, "levels": [{"name": "stage", "points": SQUARE, "height": 0.5}]}
    assert list(scene_library.shell_kinds(level)) == ["floor"] and scene_library.shell_kinds({"w": 6.0, "d": 4.0}) == {}
    # a glass roof the shell lays is asked its own glass kind, answered as clear glass the flat surface sees through
    # (2026-11-15: asked none, the greenhouse's glass dome took its roof's surface and stood opaque)
    domed = {"w": 6.0, "d": 4.0, "walls": [{}], "roofs": [{"kind": "dome", "points": SQUARE, "eave": 2.5, "top": 4.0}]}
    glass_rows = [{"part": "roof", "name": "glass dome roof", "noun": "roof"}]
    assert "glass" in scene_library.shell_kinds(domed, glass_rows) and "glass" not in scene_library.shell_kinds(domed)
    glazed_answer = {"surfaces": [
        {"name": "dome glazing", "family": "glass", "recipe": "glass", "token": "t", "roughness": 0.05, "metal": 0.0,
         "sound": "glass", "kinds": ["glass", "roof"]},
        {"name": "dark pane", "family": "glass", "recipe": "glass", "token": "t", "roughness": 0.05, "metal": 0.0,
         "sound": "glass", "kinds": ["window"]},
        {"name": "frame paint", "family": "paint", "recipe": "painted_metal", "token": "t", "roughness": 0.5,
         "metal": 0.0, "sound": "metal", "kinds": ["glass"]}]}
    glazed = scene_library.library_of("dome", json.dumps(glazed_answer), {"tokens": {"t": "#808080"},
                                                                          "wear": {"dirt_token": "t"}},
                                          json.loads(METHOD.read_text()))
    panes = glazed["families"]["glass"]["variants"]
    assert panes["dome_glazing"]["opacity"] == scene_library.CLEAR_GLASS and "opacity" not in panes["dark_pane"]
    assert "opacity" not in glazed["families"]["paint"]["variants"]["frame_paint"]
    glass_kind = {"glass": scene_library.GLASS_SHELL_WORDS}
    assert not [found for found in scene_library.library_findings(glazed, glass_kind, {"glass", "metal"})
                if "clear glass" in found]
    unglazed = dict(glazed, kinds={"glass": ["frame_paint"]})
    assert [found for found in scene_library.library_findings(unglazed, glass_kind, {"glass", "metal"})
            if "clear glass" in found], "a glass kind answered with no glass recipe passes"
    assert scene_library.shows_picture("Wall posters") and scene_library.shows_picture("oil canvas")
    assert not scene_library.shows_picture("laser printer") and not scene_library.shows_picture("glass pane")
    # every old material retired (owner, 2026-10-21): the repository's library is the method alone, and a reader of a
    # surface gets the missing input named, never a KeyError
    method = library.theme_library()
    assert method["families"] == {} and method["tokens"] == {} and method["pictures"] == {}, method
    assert set(method["recipes"]) and set(method["wear_levels"]) == {"new", "worked", "worn"}
    assert not [setting for defaults in method["recipes"].values() for setting in defaults
                if isinstance(defaults[setting], str)], "a recipe default names an old token"
    assert library.library_specs() == {} and library.variants(method) == {}  # a lookup finds no surface
    for read in (lambda: library.spec(method, "painted_panel", "hull-trim", {}),
                 lambda: route_list.palette_library.specs(PALETTE)):
        with pytest.raises(library.LibraryEmpty) as empty:
            read()
        assert library.EMPTY in str(empty.value), empty.value
    # a flat sheet (stairwell's door mat, quarters' rug and sticky note, 2026-11-08) is marked a sheet in the question
    # and offered recipes that draw a pile and writing in the library's own colours, its rule the bake's
    assert method["colour_settings"]["pile"] == method["colour_settings"]["written"] == ["second"]
    data = {"takes": {"rug-t1": {"kind": "rug", "object": "patterned rug"},
                      "note-t1": {"kind": "note", "object": "sticky note"},
                      "crate-t1": {"kind": "crate", "object": "crate"}},
            "bake": {"models": {"rug_1": "rug-t1", "note_1": "note-t1", "crate_1": "crate-t1"},
                     "entries": {"rug_1": {"size": [2.0, 0.02, 3.0]}, "note_1": {"size": [0.08, 0.001, 0.08]},
                                 "crate_1": {"size": [0.6, 0.4, 0.5]}}}}
    with tempfile.TemporaryDirectory() as temporary:
        (pathlib.Path(temporary) / "place.json").write_text(json.dumps(data))
        kinds = scene_library.kinds_of({"surfaces": pathlib.Path(temporary) / "place.json"})
    assert kinds == {"crate": "crate", "note": "sticky note" + scene_library.SHEET_WORDS,
                     "rug": "patterned rug" + scene_library.SHEET_WORDS}, kinds
    from score.stages.props import flat_sheet
    with prop_data.tools("props/closeup", "props"):
        import check
    assert (scene_library.SHEET_FLAT, scene_library.SHEET_MIDDLE) == (flat_sheet.SHEET_SHARE, check.SLENDER_SHARE)
    for size in ([2.0, 0.02, 3.0], [0.08, 0.001, 0.08], [0.6, 0.4, 0.5], [0.4, 0.01, 4.0], [0.2, 0.517, 0.02]):
        assert scene_library.sheet_sized(size) == flat_sheet.sheet({"size": size, "name": "rug"}), size
    # only a line no scene owns reads every locked concept and its takes' close-ups; a scene declares its own, locked
    # yet or not, so a scene with none (environment 1's launch) blocks on it by name instead of being asked over every
    # other scene's
    assert scene_palette.files("people")["concepts"] == "{home}/design/concepts"
    for scene in ("cockpit", "no-such-scene"):
        found = scene_palette.files(scene)
        assert found["concept"] == "{home}/design/concepts/" + f"{scene}.png" and "concepts" not in found, found
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
    assert "pixal" in palette.after and not palette.selects, palette.after  # it waits on the row that leaves them
    # the bodies' faces: with no concept locked the rows read today's (body_faces.concept), every body that does not
    # shine a paid world row of its own, its physics from the cited table and its ground by them, no name read
    monkeypatch.setattr(body_faces.environment_concept, "in_force", lambda store: None)
    faced = body_faces.rows(None)
    assert [row.name for row in faced] == ["body-face-earth", "body-face-moon", "body-face-mars"]  # not the Sun
    assert all(row.paid and row.grain == "world" and row.euros == body_faces.FACE_EUROS for row in faced)
    runner = type("Runner", (), {"store": None})
    moon = body_faces.body_param("moon")(runner)
    assert moon["radius_km"] == settings.reference()["bodies"]["moon"]["radius_km"]  # the cited table's value
    assert "radius 1,737 km" in body_faces.facts_of(moon)
    grounds = {key: body_faces.ground_param(key)(runner)[0] for key in ("earth", "moon", "mars")}
    assert grounds == {"earth": "ocean", "moon": "regolith", "mars": "sand"}
    assert body_faces.style_param(runner) == body_faces.environment_concept.style_now()
    asked = []
    for case, body, style, ground, reply, raised, made in FACES:
        monkeypatch.setattr(body_faces.route_ask, "asked", lambda bodies, caller, case=case, reply=reply:
                            asked.append((case, bodies, caller)) or {key: reply for key in bodies})
        with tempfile.TemporaryDirectory() as temporary:
            out = pathlib.Path(temporary)
            with pytest.raises(ValueError, match=raised) if raised else contextlib.nullcontext():
                body_faces.make_face({"library": str(METHOD)}, out, 0, {"body": body, "style": style, "ground": ground})
            assert (out / "face.json").exists() == bool(made), case
            assert raised or body_faces.judge_face(out, {}, {}).answer == ("pass" if made else "fail"), case
            face = json.loads((out / "face.json").read_text()) if made else None
            assert (face and {field: face[field] for field in made}) == made, (case, face)
            if made:
                faced_library = json.loads((out / "materials.json").read_text())
                assert body_faces.face_findings(body["body"], faced_library) == [], case
                assert faced_library["families"]["regolith"]["variants"]["moon_face"]["second"] == "crater-dark"
                assert abs(face["colour"][0] - 0.2541) < 1e-3  # #8a = 138: sRGB to linear
    assert [(case, caller) for case, _, caller in asked] == [(FACES[0][0], "body-face"), (FACES[1][0], "body-face")]
    bodies = asked[0][1]  # the moon's one ask: its style, its physics, the recipe its ground names alone
    schema = bodies["moon"]["generationConfig"]["responseSchema"]["properties"]["face"]
    assert "worn NASA-punk" in json.dumps(bodies["moon"]) and "airless" in json.dumps(bodies["moon"])
    assert schema["properties"]["recipe"]["enum"] == ["regolith"], schema
    assert schema["properties"]["colours"]["required"] == ["second"] and "colours" in schema["required"], schema
    off = body_faces.library_of("mars", json.dumps(ANSWER), json.loads(METHOD.read_text()))
    off["families"]["regolith"]["variants"]["mars_face"].update(token="rust", recipe="moon_dust", roughness=1.5)
    found = body_faces.face_findings("mars", off)
    for words in ("recipe moon_dust", "token rust", "moon_dust is no natural ground", "roughness 1.5"):
        assert any(words in fault for fault in found), (words, found)
    # the stage table's palette, library, list and recheck rows ask the claude-code adapter only for the make's own
    # call; body-face still asks route_ask (Gemini); a palette answer its palette_of refuses is asked once more
    sent, first = [], [OFF_PALETTE]

    def claude_asked(bodies, caller):
        sent.append((caller, bodies))
        told = any("cannot be used" in part.get("text", "") for body in bodies.values() if body
                   for part in body["contents"][0]["parts"])
        return {take: json.dumps(ON_PALETTE if told else first[0]) for take, body in bodies.items() if body}
    monkeypatch.setattr(claude_asks.claude_code, "asked", claude_asked)
    for name, module in {"finish-route-palette": scene_palette, "surface-library": scene_library,
                         "finish-route-list": route_list, "finish-route-recheck": route_recheck}.items():
        assert ROWS[name].make.__wrapped__.__module__ == module.__name__, name
        gemini = module.ask

        def asks_once(inputs, out, seed, params, module=module):  # the make, its one batch of asks alone
            return module.ask({"k": {}})
        asks_once.__module__ = module.__name__
        claude_asks.asking_claude(asks_once)({}, None, 0, {})
        assert module.ask is gemini, name
    assert [caller for caller, _ in sent] == [scene_palette.CALLER, scene_library.CALLER, route_list.CALLER,
                                              route_recheck.CALLER]
    assert not hasattr(ROWS["body-face-earth"].make, "__wrapped__")
    assert "claude_code" not in inspect.getsource(body_faces) and "route_ask.asked" in inspect.getsource(body_faces)
    bodies = {"cockpit": scene_palette.palette_body([], LEVELS)}
    asked_as = copy.deepcopy(bodies)
    for case, module, answer, asks in REPAIRS:
        sent.clear()
        first[0] = answer
        answers = claude_asks.answered(bodies, module)
        assert len(sent) == asks and answers, (case, sent)
        assert module is not scene_palette or scene_palette.palette_of(answers["cockpit"], LEVELS)["wear"][
            "dirt_token"] == "soot-grime", case  # the told answer kept
        for _, again in sent[1:]:
            told = again["cockpit"]["contents"][0]["parts"][-1]["text"]
            assert "soot-grime" in told and "cannot be used" in told and "worn" in told, (case, told)
    assert bodies == asked_as  # the first body kept as it was asked
    # an ask's answer (finish_ask.generated, GENERATED): a refusal is asked again, at most REFUSED_ASKS times in all,
    # the room checked before every send; anything else reaches the row, a lost connection as no answer
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import google_spend
    with pytest.MonkeyPatch.context() as asking:  # Google's faked answers end with this block
        asking.setattr(finish_ask, "REFUSED_WAIT", 0)
        for case, faults, raised, asks in GENERATED:
            tiers, rooms = [], []

            def answer(model, body, key, timeout, caller, cache, faults=faults, tiers=tiers):
                tiers.append(body.get("serviceTier"))
                if len(tiers) <= len(faults):
                    raise faults[len(tiers) - 1]
                return "answered"
            asking.setattr(google_spend, "generate", answer)
            with pytest.raises(raised) if raised else contextlib.nullcontext():
                found = finish_ask.generated(finish_ask.LIST_MODEL, {"serviceTier": "flex"}, "key", 1, "test", False,
                                             room=lambda rooms=rooms: rooms.append(1))
                assert found == "answered", (case, found)
            assert tiers == ["flex"] * asks and len(rooms) == asks, (case, tiers, rooms)
        # a batch's answers (route_ask.asked, ASKED), outside a cleared run: Gemini is sent a batch (and the key read)
        # only when the cache cannot answer it whole and the run is cleared; an answer that does not parse is a gap
        real, sent = route_ask.google_batch.generate, []
        asking.delenv(compute.TICKET, raising=False)
        asking.setattr(route_ask.finish_ask, "secret_key", lambda: "key")
        asking.setattr(route_ask.google_batch, "generate",
                       lambda model, batch, key, caller: sent.append(key) or (
                           real(model, batch, key, caller) if key is None else {}))  # only the cache, never Google
        for case, cached, names, expected, kept, sent_keys in ASKED:
            sent.clear()
            batch = {name: {"ask": name} for name in names}
            for name, response in cached.items():
                route_ask.google_spend.keep(route_ask.google_spend.cache_path(finish_ask.LIST_MODEL, batch[name]),
                                            response)
            if isinstance(expected, type):
                with pytest.raises(expected):
                    route_ask.asked(batch, "test")
            else:
                found = route_ask.asked(batch, "test")
                assert found.keys() == expected.keys() and all(
                    isinstance(found[name], want) if isinstance(want, type) else found[name] == want
                    for name, want in expected.items()), (case, found)
            assert {name for name in names if route_ask.google_spend.cache_path(
                finish_ask.LIST_MODEL, batch[name]).exists()} == kept, case
            assert sent == sent_keys, (case, sent)
    # the recheck's question words each finish in the token it is drawn and baked in (WORDED)
    for case, given, holds, lacks in WORDED:
        line = route_recheck.finish_lines(
            [{"finish": "brown fabric", "parts": "patches", "surface": "suit_patches", "settings": given}],
            {"suit_patches": {"family": "fabric", "colour": [1.0, 0.0, 0.0]}},
            {"glass-brown": [0.31855, 0.13287, 0.0331]})
        assert all(words in line for words in holds) and not any(words in line for words in lacks), (case, line)
    import base_level  # by its bare name, as the bake's card runs it
    import feet  # as the paint reads its feet
    import feet_stand  # by its bare name, as the table sets it on the row
    records = {}  # each levelled take's record, judged below
    for case, mesh, tall, expect in LEVELLED:
        vertices, faces = mesh()
        points, record = place_line.levelled_feet(vertices, faces, **({"tall": tall} if tall else {}))
        records[case] = record
        assert all(record[key] == expect[key] for key in ("feet", "refused") if key in expect), (case, record)
        assert "levelled" not in expect or len(record["levelled"]) == expect["levelled"], (case, record)
        assert "far" not in expect or abs(points[:, 1][vertices[:, 2] > expect["far"]].min()) < 1e-9, (
            case, "its short foot not down")
        if "even" in expect:
            lows = [low for _, low in feet.feet(feet.surface_points(points, faces), expect["even"], 0.05)]
            assert len(lows) == expect["feet"] and max(lows) - min(lows) < 1e-9, (case, lows)
        if expect.get("rests"):
            assert record.get("rests") and resting_lean(vertices, faces) > 1.0 > 0.1 > resting_lean(points, faces), (
                case, record)
        elif "rests" in expect:
            assert "rests" not in record and np.array_equal(points, vertices), (case, record)
    paint, bake_row = ROWS["surfaces-paint"], ROWS["surfaces-bake"]
    assert "feet in one plane" in [check.name for check in paint.checks] and paint.make is feet_stand.make_paint
    judges = {"place_line": place_line.judge_feet, "feet_stand": feet_stand.judge_feet}
    with tempfile.TemporaryDirectory() as temporary:
        for case, judge, take, found, model, verdict, named in FEET_JUDGED:
            folder = pathlib.Path(temporary) / case
            (folder / "bake" / "entries").mkdir(parents=True)
            (folder / "bake" / "entries" / f"{take}.json").write_text(json.dumps({take.rsplit("-", 1)[0] + "_1": {}}))
            if model is not None:
                baked_model(folder / "bake", take.rsplit("-", 1)[0] + "_1", model())
            (folder / "painted.json").write_text(json.dumps({"takes": {take: {"feet": records[found] if isinstance(found, str) else found}}}))
            judged = judges[judge](folder, {"surfaces-bake": folder / "bake"} if judge == "feet_stand" else {}, None)
            assert judged.answer == verdict and (named is None or named in judged.findings[0]), (case, judged)
    for case, points, highest, tolerance in STANCES:
        assert abs(max(bake_check.stance_lows(points)) - highest) <= tolerance, case
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        rows = [{"id": "parts_rack_1", "name": "steel parts rack"}, {"id": "leg_strut", "name": "torn-off landing leg"}]
        for labels, row, stands in STANDS:
            (folder / "labels.json").write_text(json.dumps({"feet": labels}))
            assert bake_check.stands(row, folder, rows, ["torn"]) is stands, (labels, row)
        (folder / "checks.json").write_text(json.dumps({
            "parts_rack_1": {"stands": True, "stance_lows": [0.0, 0.221, 0.0, 0.24]},
            "leg_strut": {"stands": False, "stance_lows": [0.0, 0.3, 0.2, 0.0]},
            "crate": {"stands": True, "stance_lows": [0.0, 0.01, 0.0, 0.02]},
            "rover_1": {"stands": True, "on_feet": 5, "stance_lows": [0.0, 0.56, 0.0, 0.0]},
            "table_1": {"stands": True, "on_feet": 4, "stance_lows": [0.0, 0.1, 0.1, 0.0]}}))
        verdict = bake_check.judge_stance(folder, {}, None)
        (folder / "labels.json").write_text(json.dumps({"feet": {"feet": 5}}))
        assert bake_check.feet_of(folder) == 5 and bake_check.STANCE_FEET == base_level.ON_FEET
    # on five feet the rover stands on three quadrants, its tube hanging over the fourth; a table on four with two
    # quadrants off the floor does not
    assert verdict.answer == "fail" and len(verdict.findings) == 2 and "parts_rack_1: a foot 24.0 cm" in \
        verdict.findings[0] and "table_1" in verdict.findings[1]
    assert set(json.loads((REPO / "data/checks/stance.json").read_text())) == {"about", "lies"}
    steps = {"flattened": place_line.flattened_base, "sloped": place_line.sloped_base}
    based = {}
    for case, made, step, arguments, expect in BASES:
        base = made()
        points, record = steps[step](base, *arguments)
        based[case] = record
        assert all(record[key] == expect[key] for key in ("flattened", "refused") if key in expect), (case, record)
        rise = expect.get("rise", ABSENT)
        if isinstance(rise, str):
            assert record["refused"] == [based[rise]["rise"]], (case, record)
        elif rise is None:
            assert record["rise"] is None, (case, record)
        elif rise is not ABSENT:
            assert abs(record["rise"] - rise) < 0.01, (case, record)
        assert "quadrants" not in expect or max(record["quadrants"]) < expect["quadrants"], (case, record)
        if "down" in expect:
            under, tolerance = expect["down"]
            assert np.abs(points[under(base), 1]).max() < tolerance, (case, "not brought down")
        assert "kept" not in expect or np.allclose(points[expect["kept"](base)], base[expect["kept"](base)]), (
            case, "a point over the band moved")
        assert not expect.get("as made") or np.array_equal(points, base), (case, "not left as made")
        assert not expect.get("above lowest") or points[:, 1].min() >= base[:, 1].min() - 1e-12, (
            case, "brought down past the lowest point")
    box = trimesh.creation.box(bounds=((-5.0, 0.0, -5.0), (5.0, 2.0, 5.0))).subdivide().subdivide().subdivide()
    corner = (box.vertices[:, 0] >= 0) & (box.vertices[:, 2] >= 0) & (box.vertices[:, 1] < 1e-9)
    for up, tall, moves in HALLS:
        hall = np.asarray(box.vertices).copy()
        hall[corner, 1] += up
        was, _ = place_line.levelled_feet(hall, box.faces, tall)
        now, report = base_level.levelled_feet(hall, box.faces, tall)
        assert np.array_equal(was, now) != moves, (up, tall)
        if moves:  # in metres through its standing height: 8 cm up as the paint left it, level now
            assert max(bake_check.stance_lows(was * 10.0)) > 0.03 >= max(bake_check.stance_lows(now * 10.0))
            assert report["flattened"], report
    # a body on three legs, its fourth quadrant's underside hanging over (old_station's rover, score #156): the paint
    # brings that underside down to the floor, the bake's paint (base_level) leaves it as the feet stand
    stool = on_three_legs()
    was, _ = place_line.levelled_feet(stool.vertices, stool.faces, 1.5)
    now, report = base_level.levelled_feet(stool.vertices, stool.faces, 1.5)
    over = (stool.vertices[:, 0] < 0) & (stool.vertices[:, 2] > 0) & (stool.vertices[:, 1] < 0.31)
    assert report["feet"] == 3 and report["base_left"] and not report["flattened"], report
    assert was[over, 1].min() < 0.1 and np.array_equal(now, stool.vertices), "the overhang brought down"
    # four wheels on one plane leaning off level and a lone leg reaching under it (old_station's rover, score #156):
    # the paint stretches the wheels down to the leg; the bake's paint turns the take onto its wheels' plane, every
    # wheel kept as it was made, and cuts the leg at it, the finished box turned with it. Feet on one leaning plane
    # with none lone, or under a body standing level, are levelled as before.
    for case, leg, leaning, turned in FLOORS:
        rover, wheels, legged = on_its_floor(leg, leaning)
        was, _ = place_line.levelled_feet(rover.vertices, rover.faces)
        now, report = base_level.levelled_feet(rover.vertices, rover.faces)
        spread = lambda points, wheel: np.linalg.norm(points[wheel] - points[wheel].mean(axis=0), axis=1)  # noqa: E731
        kept = [np.abs(spread(points, wheel) - spread(rover.vertices, wheel)).max() for points in (was, now)
                for wheel in wheels]
        if not turned:
            assert "turned" not in report and np.array_equal(was, now), (case, report)
            continue
        assert report["turned"] == [pytest.approx(math.degrees(math.atan(FLOOR_RISE)), abs=0.1)], (case, report)
        assert max(kept[:4]) > 0.05 and max(kept[4:]) < 1e-9, (case, "every wheel as it was made", kept)
        bottoms = [now[wheel, 1].min() for wheel in wheels]
        assert np.ptp(bottoms) < 0.01 and abs(now[legged, 1].min() - min(bottoms)) < 0.01, (case, bottoms)
        bounds = np.array([rover.vertices.min(axis=0), rover.vertices.max(axis=0)])
        boxed = base_level.boxed(lambda *written: written[5])(None, None, None, None, None, bounds, None)
        assert ((now >= boxed[0] - 1e-9) & (now <= boxed[1] + 1e-9)).all(), (case, "the box turned with it")
        assert not ((now >= bounds[0] - 0.02) & (now <= bounds[1] + 0.02)).all(), (case, "the box unturned cuts")
    slab = trimesh.creation.box(bounds=((-1.0, 0.0, -1.0), (1.0, 2.0, 1.0))).subdivide().subdivide().subdivide()
    bottom = np.asarray(slab.vertices)[:, 1] < 1e-9
    for rise, rough, acts in CAPPED_PLANES:
        base = np.asarray(slab.vertices).copy()
        base[bottom, 1] += rise * (base[bottom, 0] + 1.0) / 2.0 + rough * (np.arange(bottom.sum()) % 2)
        before = place_line.sloped_base(base, 0.5, 0.17, 0.03, 0.4)
        after = base_level.capped_plane(place_line.sloped_base, 0.005)(base, 0.5, 0.17, 0.03, 0.4)
        assert (after[1]["rise"] is not None) == acts, (rise, after[1])
        if before[1]["rise"] is not None:
            assert np.array_equal(before[0], after[0]), "as the paint brought it down before"
    assert all(getattr(place_line, name).__module__ == "place_line" for name in base_level.BASE_STEPS), "let go"
    with base_level.held():
        assert base_level.place_line.levelled_feet is base_level.levelled_feet, "the bake's paint levels by base_level"
    assert place_line.levelled_feet is base_level.PAINTS_LEVEL, "and lets go"
    assert "score/stages/surfaces/base_level.py" in (REPO / "score/stages/surfaces/inside/paint_fit.py").read_text()
    assert bake_row.files("base")["paint bake base_level.py"].endswith("score/stages/surfaces/base_level.py")
    # one world of the two boxes listed, split and parted (the colour check held wide, 1000, or at 0.5) carries the
    # recheck (RECHECKS), the picks row and the parts it makes (PICKS, REMADE, FINISH_FOR, COLOUR_FITTING), then the
    # bake and the paint's colour gate on it (CONSOLES)
    from score.stages.surfaces import colour_picks
    world = pathlib.Path(tempfile.mkdtemp())
    split_of = {}
    for listing in (two_finish_answer, grey_over_blue):
        (world / listing.__name__).mkdir()
        split_of[listing] = split(world / listing.__name__,
                                  listed(world / listing.__name__, lambda views, take, listing=listing: listing(views))[0])
    parts_of = {}
    for delta in (1000.0, 0.5):
        with monkeypatch.context() as held:
            held.setattr(finish_parts, "COLOUR_DELTA_E", delta)
            (world / f"parts {delta}").mkdir()
            parts_of[delta] = parted(world / f"parts {delta}", split_of[two_finish_answer])
    for case, delta, answer, (asks, passed, suggested, fault, faulted), (judged, finding) in RECHECKS:
        out = world / f"recheck {case}"
        with monkeypatch.context() as held:
            held.setattr(finish_parts, "COLOUR_DELTA_E", delta)
            record, verdict, asked = recheck_made(parts_of[delta], out, answer)
        assert len(asked) == asks and record["asked"] is bool(asks) and record["passed"] is passed, (case, record)
        assert record["suggested"] == suggested and bool(record["colour_faults"]) is faulted, (case, record)
        assert record["fault"] is None if fault is None else record["fault"].startswith(fault), (case, record)
        assert verdict.answer == judged and (finding is None or finding in verdict.findings[0]), (case, verdict)
        assert (out / TAKE / "checked-front.png").exists() is bool(asks), case
    for case, listing, change, token, not_picked, by in PICKS:
        answer = None if change is None else {"finishes": [{**FAILING_RED, **change},
                                                           {"finish": 2, "matches": True, "why": "blue"}]}
        asked, picked, made, plain = picks_made(split_of[listing], world / f"picks {case}", answer)
        found = json.loads((picked[recheck_picks.ROW] / "picks.json").read_text())
        record = json.loads(made)["takes"][TAKE]
        assert (TAKE in asked) is (answer is not None), (case, asked)  # a take the free colour check failed: unasked
        assert not (picked[recheck_picks.ROW] / "batch-gaps.json").exists(), case  # a recheck fail is a pick, no gap
        verdict = recheck_picks.judge_picks(picked[recheck_picks.ROW], split_of[listing], {})
        assert verdict.answer == "pass" and verdict.measures["picked_takes"] == (token is not None), (case, verdict)
        assert [finish["by"] for finish in record["finishes"]] == by, (case, record["finishes"])
        if token is None:  # the parts made as they were, byte for byte, so nothing after them moves
            assert found["takes"] == {} and not_picked in found["not_picked"][TAKE] and made == plain, (case, found)
            continue
        pick = found["takes"][TAKE]["1"]
        assert pick["token"] == token and pick["delta_e"] <= finish_parts.COLOUR_DELTA_E, (case, found)
        red = record["finishes"][0]
        assert red["settings"]["token"] == token and red["settings"]["roughness"] == 0.2, red
        assert red["settings"]["seed"] == pick["was"]["settings"]["seed"] and red["picked"]["why"], red
        assert red["delta_e"] <= finish_parts.COLOUR_DELTA_E, red  # the parts' own check
        assert {row["settings"]["token"] for row in record["parts"] if row["words"] == "red paint"} == {token}, case
        assert made != plain, case
        kept_pick, kept_rows, kept_plain = pick, picked, json.loads(plain)
    other = world / "other list"  # the list cut to its first finish: the split was made on another list
    shutil.copytree(kept_rows["finish-route-list"], other)
    entry = json.loads((other / f"{TAKE}.json").read_text())
    (other / f"{TAKE}.json").chmod(0o644)
    (other / f"{TAKE}.json").write_text(json.dumps({**entry, "finishes": entry["finishes"][:1]}))
    for case, number, change, (token, dropped, gate, refused) in REMADE:
        takes = {} if change is None else {TAKE: {number: dict(kept_pick, **change)}}
        if refused is not None:
            with pytest.raises(ValueError, match=refused):
                remade_parts({**kept_rows, "finish-route-list": other}, takes, world)
            continue
        made, picks = remade_parts(kept_rows, takes, world)
        assert recheck_picks.judge_picks(picks, kept_rows, {}).answer == gate, case
        if dropped is None:
            assert made["takes"][TAKE]["finishes"][0]["settings"]["token"] == token, (case, made)
            assert "picks_dropped" not in made, (case, made)
        else:
            assert dropped in made["picks_dropped"][TAKE][0] and made["takes"] == kept_plain["takes"], (case, made)
    for case, name, number, taken, expected in FINISH_FOR:
        assert recheck_picks.finish_for(name, number, FINISH_LIST, taken) == expected, case
    tokens = library.token_colours({"tokens": TOKENS})
    seen_blue = finish_parts.library_lab({"colour": tokens["bay-three"]}).tolist()
    off = {"finish": "blue steel", "surface": "bare_steel", "by": "off its colour", "measured_lab": seen_blue,
           "delta_e": 55.5, "settings": {"token": "steel", "roughness": 0.4, "metal": 1.0, "seed": 3},
           "looks": {"listed": {"recipe": "bare_metal",
                                "lab": finish_parts.library_lab({"colour": tokens["steel"]}).tolist()}}}
    fitting = {"finish": "red paint", "surface": "red_paint", "by": "the list",
               "measured_lab": off["looks"]["listed"]["lab"]}
    for case, beside, words, picked_as, why in COLOUR_FITTING:
        found, given = colour_picks.colour_fitting([fitting] * beside + [dict(off, finish=words)], tokens)
        if picked_as is None:
            assert found == {} and why in given, (case, found, given)
            continue
        key, token = picked_as
        assert given is None and list(found) == [key] and found[key]["token"] == token, (case, found, given)
        assert found[key]["by"] == colour_picks.BY, (case, found)
        assert (found[key]["roughness"], found[key]["metal"]) == (0.4, 1.0), (case, found)
        assert colour_picks.recheck_picks.with_pick(off, found[key], tokens)["settings"]["token"] == token, case
    assert inspect.unwrap(ROWS[colour_picks.recheck_picks.ROW].make) is colour_picks.make_picks
    # the bake paints and bakes each take in one card job with the list's settings, and the paint takes it over
    with monkeypatch.context() as held:
        held.setattr(finish_parts, "COLOUR_DELTA_E", 1000.0)  # every finish keeps its listed surface, so its settings
        rows = parts_of[1000.0]
        inputs, out, calls = bake_made(world, rows)
    parts = json.loads((rows["surfaces-parts"] / "parts.json").read_text())["takes"][TAKE]["parts"]
    assert all(row["settings"] for row in parts), parts
    assert len(calls) == 1 and pathlib.Path(calls[0]["command"][1]).name == "blender_cloud.py", calls
    assert calls[0]["command"][-1] == route_bake.place_line.CLASSES  # the bake's cards, one call
    (job,) = calls[0]["jobs"]
    assert job["script"] == route_bake.SCRIPT and str(route_bake.made_of(out, TAKE)) in job["outputs"], job
    assert (out / "made" / "two_boxes.gltf").read_text() == "{}"  # gathered where its readers find it
    records = calls[0]["files"][f".bake-{TAKE}-records.json"]
    head = calls[0]["files"][f".bake-{TAKE}-head.json"]
    assert head["models"] == ["two_boxes"], head
    assert (head["wear"], head["dirt"]) == (0.4, 0.3), head  # the scene palette's, not place.json's
    for record, row in zip(records, parts):
        assert record["surface"] == route_settings.settings_name(row["judge"], row["settings"]), record
        spec = head["specs"][record["surface"]]
        assert spec["library"] == row["judge"] and spec["token"] == row["settings"]["token"], spec
        assert spec["colour"] == tokens[row["settings"]["token"]], spec
        assert spec["roughness"] == row["settings"]["roughness"] == 1.0, spec  # the list's 1.4, clipped
        assert spec["seed"] == row["settings"]["seed"] and spec.get("wear") == row["settings"].get("wear"), spec
    # the blue finish's own wear (a cause given) rides its spec; the red one's level without a cause is not taken
    assert sorted(spec.get("wear", 0) for spec in head["specs"].values() if "settings" in spec) == [0, 0.8]
    assert json.loads((out / "specs.json").read_text()) == head["specs"]
    assert json.loads((out / "baked.json").read_text())["two_boxes"]["parts"] == TAKE
    assert not list(out.glob(".bake-*"))  # the jobs' files are gone
    assert route_bake.bake_faults(out) == [] and route_bake.judge_baked(out, inputs, {}).answer == "pass"
    # the measure runs in the prop environment on the baked .gltf; here in-process on the console's triangles
    gate = next(check for check in route_paint.paint_gates() if check.name == baked_colour.GATE)
    assert inspect.unwrap(next(check for check in ROWS["surfaces-paint"].checks
                               if check.name == baked_colour.GATE).judge) is baked_colour.judge_colour
    monkeypatch.setattr(baked_colour, "measured", lambda inputs, made: baked_colour.measure_step(
        baked_colour.prop_env.short(inputs), made))
    for case, rusted, offs, (judged, baked_off, findings), gap_checks in CONSOLES:
        with monkeypatch.context() as held:
            held.setattr(baked_colour, "measure_model", lambda model, entry, bake, specs: console_bake(rusted))
            painting = world / f"paint {case}"
            painting.mkdir()
            route_paint.make_paint({"surfaces-bake": out}, painting, 7, {})
            verdict = gate.judge(painting, {"surfaces-bake": out}, {})
        painted = json.loads((painting / "painted.json").read_text())
        measure = painted["takes"][TAKE].pop(baked_colour.FIELD)
        assert painted == json.loads((out / "painted.json").read_text()), case  # the bake's, its measure beside
        assert (painting / "labelled" / TAKE / "labels.json").exists(), case
        assert {surface: entry["off"] for surface, entry in measure["two_boxes"].items()} == offs, (case, measure)
        assert (verdict.answer, verdict.measures["baked off"], verdict.findings) == (judged, baked_off, findings), \
            (case, verdict)
        gaps = painting / "batch-gaps.json"
        assert ([gap["check"] for gap in json.loads(gaps.read_text())["gaps"]] if gaps.exists() else None) == \
            gap_checks, case
    assert gate.judge(out, {"surfaces-bake": out}, {}).answer == "unknown"  # the bake's own, no measure
    # a take's bake job carries its own parts and its own specs alone, so its kept content moves when its own take
    # changes and never when another take of the place does (#36, 2026-10-30: each job carried the place's whole
    # parts.json, the parts output's folder and every take's specs, so one retaken take baked every take of its place
    # again); each brings its models back into a folder of its own (#36: every take brought back the row's one `made`
    # folder and named the others as its peers): OTHER a copy of the take, its first part's roughness 0.6, then 0.2
    kept_jobs, brought = stages.kept_module(), []
    with monkeypatch.context() as held:
        held.setattr(finish_parts, "COLOUR_DELTA_E", 1000.0)  # every finish keeps its listed surface and settings
        held.setattr(route_bake, "BAKE_REPO", ())  # the repository's folders: the same for every take
        held.setattr(route_bake.place_line, "PAINT_REPO", ())
        held.setenv(kept_jobs.CODE, "surfaces-bake@cockpit row-code")
        rows["surfaces"].write_text(json.dumps(dict(json.loads(rows["surfaces"].read_text()), library="cockpit",
                                                    bake={"models": {"two_boxes": TAKE, "other_box": OTHER}})))
        jobs_before, jobs_after = (
            bake_jobs(rows, two_take_parts(rows, world / f"two takes {rough}", rough), world / f"bake {rough}",
                      kept_jobs, held, brought) for rough in (0.6, 0.2))
    assert sorted(jobs_before) == sorted(jobs_after) == sorted([TAKE, OTHER]), (jobs_before, jobs_after)
    assert jobs_before[TAKE] == jobs_after[TAKE], "an unchanged take's bake job moved with another take's parts"
    assert jobs_before[OTHER] != jobs_after[OTHER], "a changed take's bake job did not move"
    assert not [(one, two) for first, second in itertools.combinations(brought, 2) for one in first for two in second
                if one.is_relative_to(two) or two.is_relative_to(one)], brought  # each job's outputs its own
    # Which takes stand on feet: one surface data folder (the bare surface_data place_line reads) and one inventory,
    # the greenhouse's hand-in, which the paint declares and reads (keyed on it, never the old concept's
    # data/inventory file) to tell a take laid loose on the floor from one held. A hangar (the bay) laid an old
    # station's parts rack (its `elsewhere`, parts_rack_1 to parts_rack_4) on the floor; the old station laid none of
    # its kind, so the rack was never levelled (2026-10-15): its paint counts the claiming place's standing rows, the
    # claimed rack row, never another of its rows. A made shell piece of its own place (route "shell", laid in Objects)
    # standing on the floor or ground is levelled the same way, through the bake's claimed rows (route_bake.laid_shell):
    # the engineroom's railing and the campgrounds' dome (checkout 68); one on a wall is not. A code build stands as its
    # code made it, whatever its rows say.
    rules, shell = REPO / "data/checks/resting.json", ("railing", "dome", "window")
    folder, design = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    kept = surfaces.data.FOLDER, prop_data.DESIGN
    surfaces.data.FOLDER, prop_data.DESIGN = folder, design
    hand_in = design / "greenhouse.json"
    hand_in.write_text(json.dumps({"place": "greenhouse", "rows": HAND_IN}))
    (folder / "greenhouse.json").write_text(json.dumps({"place": "greenhouse", "takes": {
        "gh_crate_ab12": {"place": "greenhouse", "kind": "gh_crate"}}}))
    (folder / "station.json").write_text(json.dumps({"place": "station", "takes": {
        "parts_rack-r1": {}, **{f"{piece}-r1": {"place": "station"} for piece in shell}}}))
    (folder / "station-inventory.json").write_text(json.dumps({"rows": [
        {"id": "floor_plates", "anchor": "ground", "group": "kit: floor", "route": "plan", "size": [9.0, 9.0, 0.1]},
        {"id": "wall", "anchor": "on:floor_plates", "route": "plan", "part": "wall"},
        {"id": "railing", "anchor": "on:floor_plates", "route": "shell", "thing": "prop:railing-r1"},
        {"id": "dome", "name": "habitat dome", "anchor": "ground", "route": "shell", "thing": "prop:dome-r1"},
        {"id": "window", "anchor": "on:wall", "route": "shell", "thing": "prop:window-r1"}]}))
    (folder / "bay.json").write_text(json.dumps({"place": "bay", "takes": {}, "elsewhere": {
        f"parts_rack_{number}": {"take": "parts_rack-r1", "place": "station"} for number in range(1, 5)}}))
    mark = folder / "home/work/pixal/cabinet_take.svviews/code.json"
    mark.parent.mkdir(parents=True)
    mark.write_text(json.dumps({"route": "code"}))
    try:
        assert stages.paint_inventory("greenhouse")[0] == "{home}/design/props/greenhouse.json"
        assert paint.files("greenhouse")["inventory greenhouse"][0] == "{home}/design/props/greenhouse.json"
        for entry, take, stands in STANDING:
            assert place_line.stands_on_feet(entry, hand_in, rules, *([take] if take else [])) is stands, entry
        crate = {"place": "greenhouse", "kind": "gh_crate"}  # a designed take's kind lacks its take's suffix
        assert [row["id"] for row in place_line.standing_rows(crate, hand_in, rules, "gh_crate_ab12")] == ["crate"]
        assert place_line.stands({"id": "crate", "anchor": None}, rules)  # a null anchor stands on the floor, as none
        inputs = {"surfaces": folder / "station.json", "inventory bay": hand_in, "resting rules": rules}
        claimed = place_line.claimed_rows("parts_rack-r1", inputs)
        assert claimed and {row["id"] for row in claimed} == {"parts_rack"}, claimed
        assert place_line.claimed_rows("parts_rack-r1", dict(inputs, **{"inventory bay": None})) == []
        inputs["inventory station"] = folder / "station-inventory.json"
        laid = {piece: [row["id"] for row in route_bake.laid_shell(f"{piece}-r1", inputs)] for piece in shell}
        assert laid == {"railing": ["railing"], "dome": ["dome"], "window": []}, laid
        assert route_bake.laid_shell("parts_rack-r1", inputs) == []  # no place of its own: as made
        cabinet = ({"place": "garage", "kind": "garage_control_cabinet"}, {"inventory garage": hand_in,
                                                                           "resting rules": rules})
        assert place_line.feet_rows(*cabinet, "cabinet_take")[0]
        assert place_line.feet_rows(cabinet[0], {**cabinet[1], place_line.HOME: folder / "home"}, "cabinet_take") == (
            [], {"skipped": "a code build: it stands as its code made it"})
    finally:
        surfaces.data.FOLDER, prop_data.DESIGN = kept
        shutil.rmtree(folder)
        shutil.rmtree(design)
    # The bake's machine side, one take: crane-r1 of the campgrounds, its paint job built, run (killed on its
    # machine) and its labelled folder baked. Every old material retired (owner, 2026-10-21): the job sends what the
    # paint reads (its parts, its final model, the code and the library) and brings its labelled folder back; its
    # listing names the repository (the data may lie elsewhere) and its records; a paint killed on its machine says
    # its signal and its peak; and the kit route's bake of the folder it brings back, which takes the repository's
    # library by place, names each painted surface no library holds before anything is rented, never a KeyError.
    sys.path.insert(0, str(REPO / "score/stages/surfaces/inside"))
    import layout_fit
    import paint_take
    import uv_layout
    from score.stages.surfaces import bake_fitted
    work = pathlib.Path(tempfile.mkdtemp())
    try:
        out, parts = work / "out", work / "parts"
        out.mkdir()
        (work / "surfaces.json").write_text(json.dumps({"place": "campgrounds", "library": "campgrounds", "takes": {
            "crane-r1": {"place": "campgrounds", "kind": "crane"}}, "bake": {"models": {"crane": "crane-r1"}}}))
        (work / "inventory.json").write_text(json.dumps({"rows": [{"id": "crane", "anchor": "ground",
                                                                   "thing": "prop:crane"}]}))
        inputs = {"surfaces": work / "surfaces.json", "surfaces-parts": parts,
                  "inventory campgrounds": work / "inventory.json", "resting rules": REPO / "data/checks/resting.json"}
        job = json.loads(place_line.paint_job(inputs, place_line.prop_env.short(inputs), out, "crane-r1",
                                              [{"part": 0}]).read_text())
        assert job["script"] == "score/stages/surfaces/inside/paint_take.py" and job["outputs"] == [
            str(out / "labelled" / "crane-r1")], job
        sent = set(job["inputs"])
        assert {str(parts / "crane-r1"), str(parts / "parts.json"), str(REPO / "score"), str(REPO / "tools/props"),
                str(REPO / "data/library")} <= sent, sent
        assert any(path.endswith("work/pixal/crane-r1-final.glb") for path in sent), sent
        listing = json.loads(pathlib.Path(job["args"][0]).read_text())
        assert listing["paint take"] == "crane-r1" and listing["paint repo"] == str(REPO), listing
        assert json.loads(pathlib.Path(listing["paint records"]).read_text()) == [{"part": 0}]
        # The job's paint, run on its own listing: it lays its unlibraried dark_panel part in the folder the job
        # brings back, then is killed on its machine.
        labelled = pathlib.Path(job["outputs"][0])
        code, peak = paint_take.measured([sys.executable, "-c", (
            "import json, os, pathlib, signal, sys; named = json.loads(pathlib.Path(sys.argv[1]).read_text()); "
            "folder = pathlib.Path(sys.argv[2]); folder.mkdir(parents=True); "
            "(folder / 'dark_panel.ply').write_text(named['paint take']); os.kill(os.getpid(), signal.SIGKILL)"),
            job["args"][0], str(labelled)], dict(os.environ))
        assert code == -9 and peak > 0, (code, peak)
        with pytest.raises(RuntimeError) as refused:
            place_line.baking_specs("hangar", {}, [labelled])
        assert "surfaces in no library: ['dark_panel']" in str(refused.value), refused.value
        # Which part a baked triangle is named by: every RAY_NAMED world laid once, each row's naming read off it.
        named, sampled_by = {}, {}
        for world, (boxes, subdivide, geometry, entry) in RAY_WORLDS.items():
            folder = work / world
            folder.mkdir()
            for name, bounds in boxes.items():
                mesh = trimesh.creation.box(bounds=bounds)
                (mesh.subdivide_to_size(subdivide) if subdivide else mesh).export(folder / f"{name}.ply")
            sampled_by[world] = bake_check.sampled_points(geometry, np.array([0, 0]), np.array([0, 0]),
                                                          np.array([[2, 2], [2, 2]])) if "uvs" in geometry else None
            named[world] = {sampled: bake_check.baked_surfaces(geometry, folder, entry,
                                                               *([sampled_by[world]] if sampled else []))
                            for sampled in ((False, True) if sampled_by[world] else (False,))}
        for case, world, sampled, expected in RAY_NAMED:
            names, surface, _ = named[world][sampled]
            assert [names[index] for index in surface] == expected, (case, surface)
        assert sampled_by["bowl"][1].tolist() == [0, 0], sampled_by["bowl"]  # both triangles own the one texel
        assert named["tower"][False][2][0].all(), "both parts lie within the tower triangle's reach"
        nearest = bake_check.laid_parts(work / "tower", RAY_WORLDS["tower"][3])[1].nearest.on_surface(
            [[0.4, 1.0, 0.6]])[0][0]
        assert abs(nearest[0]) <= 0.05 + 1e-9, f"the post lies nearer than the facade behind: {nearest}"
    finally:
        shutil.rmtree(work)
    # The check's reach constants are make_chunky's; street's lantern string (8 m, its wire 1 cm) has its voxel
    # follow its wire, as make_chunky's voxel_of.
    import ast
    found = {node.targets[0].id: eval(compile(ast.Expression(node.value), "make_chunky", "eval")) for node in ast.parse(
        (REPO / "tools/props/library/inside/make_chunky.py").read_text()).body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in ("REACH_VOXELS", "REACH_LEAST", "VOXEL_SHARE", "VOXEL_FINEST", "THIN_VOXELS",
                                   "SURFACE_VOXELS")}
    assert (found["REACH_VOXELS"], found["REACH_LEAST"], found["VOXEL_SHARE"], found["VOXEL_FINEST"],
            found["THIN_VOXELS"], found["SURFACE_VOXELS"]) == (
        bake_check.BAKE_REACH_VOXELS, bake_check.BAKE_REACH_LEAST, bake_check.BAKE_VOXEL_SHARE,
        bake_check.BAKE_VOXEL_FINEST, bake_check.BAKE_THIN_VOXELS, bake_check.BAKE_SURFACE_VOXELS), found
    assert abs(bake_check.bake_voxel([8.0, 0.058, 0.01]) - 0.0025) < 1e-9
    # #92: each LAYOUTS square beside the sound pair is measured as the bake wrote it and named by its one fault, the
    # sound one by none; a third of the charts too thin (THIN_SPECK) is named thin. Quarters' sticky note, 2026-11-12:
    # a model of one surface has no thin-chart fault (its strip's neighbours bake its own finish), every other
    # measure still counts. A split corner at a hard normal edge (the same position and texture coordinate twice) is
    # one chart, not two: its width the square's 2 * 512^2 / (4 * 512) texels, a lone half's 150.
    layouts = {case: [*SOUND, third if third else laid_square(0.5, 0.1, 0.4, 0.4 / (2 * uv_layout.STRETCH))]
               for case, third, _ in LAYOUTS}
    layouts["thin"] = [*SOUND, THIN_SPECK]
    records = {case: uv_layout.layout_record(uv_layout.measure(squares(*layout), [(1024, 1024)]))
               for case, layout in layouts.items()}
    for case, _, fault in LAYOUTS:
        named = uv_layout.faults(records[case])
        assert named == [] if fault is None else len(named) == 1 and named[0].startswith(uv_layout.WORDS[fault]), (
            case, named, records[case])
    assert records["sound"]["median_texels_per_m"] > 300, records["sound"]
    thin = records["thin"]
    assert thin["thin"] == round(1 / 3, 4) and [fault for fault in uv_layout.faults(thin) if fault.startswith(
        uv_layout.WORDS["thin"])], thin
    assert uv_layout.faults(thin, one_surface=True) == uv_layout.faults({**thin, "thin": 0.0}), thin
    assert uv_layout.faults({**thin, "overlap": 0.05}, one_surface=True) == uv_layout.faults(
        {**thin, "thin": 0.0, "overlap": 0.05}), thin
    cornered = squares(laid_square(0.1, 0.1, 0.5, 0.5))
    cornered["positions"] = np.concatenate([cornered["positions"], cornered["positions"][[0, 2]]])
    cornered["uvs"] = np.concatenate([cornered["uvs"], cornered["uvs"][[0, 2]]])
    cornered["triangles"][1] = [4, 5, 3]
    assert np.allclose(uv_layout.measure(cornered, [(1024, 1024)])["width"], 256.0)
    # The bake's own measure (inside/layout_fit.py) is the check's; each NEXT_STEPS layout takes its next step; the
    # faces a fold lays on one texel are the ones projected again (the two overlapping squares, not the third).
    fits = {case: layout_fit.measured(*(squares(*layouts[case])[part] for part in ("positions", "uvs", "triangles")),
                                      1024) for case in ("sound", "overlap", "thin")}
    for case in fits:
        assert abs(fits[case]["thin"] - records[case]["thin"]) < 1e-4 and abs(
            fits[case]["overlap"] - records[case]["overlap"]) < 1e-4, (case, fits[case], records[case])
    fits["passing"] = {**fits["overlap"], "overlap": 0.0064, "thin": 0.0064}
    fits["passing, not thin"] = {**fits["passing"], "thin": 0.0}
    assert [layout_fit.failing(fits[case]) for case in ("passing", "overlap", "thin")] == [False, True, True], fits
    for case, fit, side, cap, rounds, step in NEXT_STEPS:
        want = layout_fit.UNFOLD if step == "UNFOLD" else step
        assert layout_fit.next_step(fits[fit], side, cap, rounds) == want, (case, fits[fit])
    assert layout_fit.folded_faces(fits["overlap"], np.arange(6) // 2).tolist() == [0, 2], fits["overlap"]["shared"]
    # The bake runs it: its card job's script inside/paint_fit.py, set on the row alone (so no reader of
    # route_bake.py moves), declared on its row, the parts row untouched.
    fitted_row = ROWS["surfaces-bake"]
    assert fitted_row.make is bake_fitted.make_bake and fitted_row.files("airlock")[
        "paint bake layout_fit.py"].endswith("score/stages/surfaces/inside/layout_fit.py"), fitted_row.files("airlock")
    assert ROWS["surfaces-parts"].make is not bake_fitted.make_bake
    started = (REPO / bake_fitted.SCRIPT).read_text()
    assert "inside/layout_fit.py" in started.split("fitted = ")[1].split("\n")[0] and started.split(
        "subprocess.run(")[-1].startswith("fitted,"), started
    monkeypatch.setattr(route_bake, "make_bake", lambda *given: route_bake.SCRIPT)  # the script card_job reads
    monkeypatch.setattr(route_bake, "SCRIPT", route_bake.SCRIPT)
    assert bake_fitted.make_bake({}, None, 0, {}) == bake_fitted.SCRIPT
    # The check's gate judges every measured model's layout by name; a sticky note of one surface passes its thin
    # strip, a frame of two does not; a model with no layout measured is unknown.
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        judged = {}
        for case, written in (
                ("every layout", {case: {"layout": record} for case, record in records.items() if case != "thin"}),
                ("one surface", {"note": {"layout": {**thin, "sparse": 0.0}, "surfaces": {"label_yellow": {}}},
                                 "frame": {"layout": {**thin, "sparse": 0.0},
                                           "surfaces": {"label_yellow": {}, "dark_steel": {}}}}),
                ("unmeasured", {"crate": {"missing_maps": ["base_color"]}})):
            (folder / "checks.json").write_text(json.dumps(written))
            judged[case] = uv_layout.judge_layout(folder, {}, None)
    assert judged["every layout"].answer == "fail" and sorted(
        finding.split(":")[0] for finding in judged["every layout"].findings) == [
        "mirrored", "outside", "overlap", "sparse", "stretched"], judged["every layout"].findings
    assert [finding.split(":")[0] for finding in judged["one surface"].findings] == ["frame"], judged["one surface"]
    assert judged["unmeasured"].answer == "unknown", judged["unmeasured"]
    assert "texture layout sound" in [check.name for check in stages.bake_checked(
        {row.name: row for row in surfaces.ROWS}["surfaces-check"]).checks]
    # The bake's entries, laid by a stand-in library's specs and wear and the finish's own turns, its flat rows by
    # flat_fit.py as the bake's card runs it (its own interpreter, no repo path), every place's bake from git.
    import flat_fit  # by its bare name, as the bake's card runs it
    import labels
    import tumble
    script = REPO / "score/stages/surfaces/flat_fit.py"
    started = subprocess.run([sys.executable, "-I", str(script)], cwd=tempfile.gettempdir(), capture_output=True,
                             text=True, timeout=60)
    assert "ModuleNotFoundError" not in started.stderr, started.stderr[-600:]
    finish_turns = {row["take"]: row["turn"] for row in BAKE_ENTRIES if row["turn"] is not None}
    folder = a_folder()
    with monkeypatch.context() as stand_in:
        stand_in.setattr(bake_job, "specs_of", lambda library_name: {})
        stand_in.setattr(library, "wear_of", lambda place_id, *_: WEAR)
        stand_in.setattr(labels, "finish_turn", lambda take: finish_turns.get(take, np.eye(3)))
        stand_in.setattr(place_line.prop_env, "PROPS_HOME", folder)
        try:
            rules = a_pose_world(folder / "rules", {})
            for row in BAKE_ENTRIES:
                case, place, model, take, want = row["case"], row["place"], row["model"], row["take"], row["want"]
                labelled = folder / "labelled" / take
                if row["extents"] is not None:
                    a_turned_take(labelled, np.eye(3) if row["turn"] is None else row["turn"], row["extents"])
                if row["code"]:
                    mark = bake_job.code_mark(take, folder)
                    mark.parent.mkdir(parents=True)
                    mark.write_text(json.dumps({"route": "code", "rule": "thin straight (owner, 2026-10-25)"}))
                kind = {"takes": {take: {"place": place, "kind": "person"}}} if row["person"] else {}
                bake = {"models": {model: take}, "entries": {model: row["design"]} if row["design"] else {}}
                surface_record = {"place": place, "library": place, **kind, "bake": bake}
                inputs = {"surfaces": a_json_file(folder, f"surfaces-{model}", surface_record)}
                if row["inventory"]:
                    inputs[f"inventory {place}"] = a_json_file(folder, f"inventory-{model}", row["inventory"])
                if row["rules"]:
                    inputs.update({name: rules[name] for name in ("stance rules", "resting rules")})
                refusal = bake_job.refusal(model, row["design"])  # entry_of's own checks, run with no take
                assert refusal is None if "refusal" not in want else want["refusal"] in refusal, (case, refusal)
                try:
                    job, (entry,) = place_line.bake_entries(inputs, {take: labelled})
                except bake_job.NoEntry as refused:
                    assert want.get("refused", "nothing refused") in str(refused), (case, refused)
                    continue
                assert "refused" not in want, (case, entry)
                assert (job["wear"], job["dirt"]) == WEAR and job["density"] == route.NEAR, (case, job)
                assert job["faces"] == route.CHUNKY_FACES, (case, job)
                laid = {key: value for key, value in want.items() if key not in ENTRY_CHECKS}
                assert {key: entry[key] for key in laid} == laid, (case, entry)
                assert "yaw" not in want or place_route.yaw_of(entry["base"]) == want["yaw"], (case, entry)
                if "raw pose" in want:  # turned back by the finish's own turn: the raw take's box again
                    base = np.array(entry["base"]).reshape(3, 3)
                    assert np.allclose(base, want["raw pose"], atol=1e-6), (case, base)
                    raw = np.ptp(route_bake.labelled_points(labelled) @ base.T, axis=0)
                    assert np.allclose(raw, row["extents"], atol=1e-6), (case, raw)
                if "kept" in want:  # never stood square
                    kept = route_bake.stood_square({model: entry}, labelled, take, inputs, person=True)[model]
                    assert kept["base"] == entry["base"] and kept["stood"]["kept"] == tumble.PERSON, (case, kept)
            crate = a_box_take(folder / "crate", "crate-t1", (1.0, 0.5, 0.5))
            for case, degrees, words, size in REFITS:
                stood = {"crate_1": {"base": bake_job.TURNS[degrees], "size": [1.0, 0.5, 0.5],
                                     "stood": {"degrees": 9.0}}}
                refitted = bake_job.refitted(stood, {"crate_1": {"size": [1.0, 1.0, 1.0]}}, crate, **words)
                assert refitted == stood if size is None else refitted["crate_1"]["size"] == size, (case, refitted)
            # #128: laid by its width and height, its depth (its row's thinnest) free to 3 times its row's, each side
            # stretched 20% at most toward its row's: workshop's monitor take, deeper than wide, 0.38 m wide, not 0.16
            assert bake_job.fit_within([0.16, 0.09, 0.15], [0.4, 0.3, 0.1]) == [0.384, 0.216, 0.3]
            frame_row = [0.15, 0.2, 0.02]
            frame = a_box_take(folder / "frame", "frame-t1", (0.15, 0.2, 0.086))
            assert bake_job.fitted_size(frame, frame_row, bake_job.TURNS[0]) == [0.126, 0.167, 0.06]
            assert flat_fit.fitted_size(frame, frame_row, bake_job.TURNS[0]) == [0.15, 0.2, 0.06]
            for case, made, kit, size in FACE_FITS:
                assert flat_fit.face_fit(made, kit) == size, case
            for kit in ([1.0, 1.0, 1.0], [3.0, 1.5, 1.5], [8.0, 0.01, 0.01]):  # chunky, chunky, slender: not flat
                assert not flat_fit.flat(kit)
                assert flat_fit.fitted_size(crate, kit, bake_job.TURNS[90]) == bake_job.fitted_size(
                    crate, kit, bake_job.TURNS[90])
            with flat_fit.held():  # the bake's entries (laid_size) and its stood takes (refitted) lay by it
                assert bake_job.laid_size(frame, frame_row, bake_job.TURNS[0]) == [0.15, 0.2, 0.06]
                stood_frame = {"frame_1": {"base": bake_job.TURNS[0], "size": [0.035, 0.047, 0.02], "stood": {}}}
                assert bake_job.refitted(stood_frame, {"frame_1": {"size": frame_row}}, frame)["frame_1"]["size"] == [
                    0.15, 0.2, 0.06]
            assert bake_job.fitted_size is flat_fit.FITS, "and lets go"
            for path in sorted(surface_data.FOLDER.glob("*.json")):  # every place's bake is written from git
                declared = surface_data.bake_files(path.stem)
                # the work folder ({seeds}, {home}/work); a designed place's surface data, {home}/design, prepare
                # writes again
                assert not any("{home}/work" in pattern or "{seeds}" in pattern
                               for pattern in declared.values()), path.stem
                assert "library bake" in declared, path.stem
                # the old kinds' details and composites retired (2026-10-21): no bake waits on them by name
                assert not {"details", "composites"} & set(declared), path.stem
        finally:
            shutil.rmtree(folder)
    assert "score/stages/surfaces/flat_fit.py" in (REPO / "score/stages/surfaces/inside/paint_fit.py").read_text()
    assert ROWS["surfaces-bake"].files("base")["paint bake flat_fit.py"].endswith("score/stages/surfaces/flat_fit.py")
    # the views row on the two boxes, by the takes its object filter keeps, and its coverage check on an open tube
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        inputs, views = cast_views(folder)
        record = json.loads((views / "views.json").read_text())
        for case, takes, answer, finding in VIEWS_JUDGED:
            made = views if takes == [TAKE] else folder / case
            if takes != [TAKE]:
                made.mkdir()
                route_views.make_views(inputs, made, 7, {"objects": takes})
            verdict = route_views.judge_views(made, inputs, {})
            assert verdict.answer == answer, (case, verdict)
            assert (verdict.findings[0].startswith(finding) if finding else
                    verdict.measures["views_most"] == len(record[TAKE]["views"])), (case, verdict)
        assert list(record) == [TAKE], record  # the filter left other-t1 out
        assert set(route_cast.BASE) <= set(record[TAKE]["views"]), record[TAKE]["views"]
        assert record[TAKE]["close_up"] == route_data.STAND_IN
        assert record[TAKE]["paint_faces"] == record[TAKE]["faces"] == 24, record[TAKE]
        assert record[TAKE]["unseen_faces"] == 0 and record[TAKE]["seen_share"] == 1.0, record[TAKE]
        assert record[TAKE]["reachable_share"] == 1.0, record[TAKE]
        assert sorted(tuple(entry["srgb"]) for entry in record[TAKE]["regions"]) == sorted([BLUE, RED])
        assert (views / TAKE / "regions-bottom.png").exists() and (views / TAKE / "right.png").exists()
    for case, seen_share, reachable, faulted in SEEN:
        judged = route_views.take_faults(TAKE, {**record[TAKE], "seen_share": seen_share, "reachable_share": reachable})
        assert bool(judged) == faulted, (case, judged)
    tube = trimesh.creation.annulus(0.3, 0.5, 1.0)  # standing up, the base views miss part of its inside
    angles, casts = route_views.covering_views(tube)
    based = len(route_cast.BASE)
    assert list(angles)[:based] == list(route_cast.BASE) and len(angles) > based, angles
    seen = np.zeros(len(tube.faces), dtype=bool)
    for index, view in enumerate(angles):
        hit = casts[view][0][casts[view][0] >= 0]
        assert index < based or (~seen[hit]).any(), view  # each added view sees faces no chosen view saw
        seen[hit] = True
    assert seen.all(), "views added until every face is seen"
    # k-means once spent its eight regions on a texture's greys (greenhouse desk, 2026-10-29): a grey ramp, a ramp of
    # rust and 40 red pixels, and under every seed the red keeps a region of its own, the greys and the rust the rest
    greys = np.repeat(np.linspace(50, 210, 20000)[:, None], 3, axis=1)
    rust = np.stack([np.linspace(90, 170, 3000), np.linspace(70, 120, 3000), np.linspace(50, 80, 3000)], axis=1)
    pixels = np.concatenate([greys, rust, np.tile([[200, 30, 30]], (40, 1))]).astype(np.uint8)
    red = route_cast.lab_of(np.array([[200, 30, 30]]))[0]
    for seed in range(7, 12):
        centres, per_pixel = route_views.colour_regions({"front": pixels.reshape(1, -1, 3)},
                                                        {"front": np.zeros((1, len(pixels)), dtype=int)}, seed)
        assert len(centres) <= route_views.REGIONS and np.linalg.norm(centres - red, axis=1).min() < 5, (seed, centres)
        assert len(np.unique(per_pixel["front"][0, -40:])) == 1  # one region holds the red, and only the red
        assert not np.isin(per_pixel["front"][0, :-40], per_pixel["front"][0, -40:]).any(), seed
    # the list, split and parts rows on the two boxes, each world's batches faked (LISTED)
    worlds = {}
    for case, (colours, answer, again, takes, laid), (asks, used, again_words, past_views, last_words), \
            list_judged, split_judged, parts in LISTED:
        folder = pathlib.Path(tempfile.mkdtemp())
        with monkeypatch.context() as tinted:
            tinted.setattr(sys.modules[__name__], "RED", colours[0])
            tinted.setattr(sys.modules[__name__], "BLUE", colours[1])
            rows, asked = worlds[case] = listed(folder, answer, takes, again, labelled_close_up=laid == "views")
            assert len(asked) == asks and all(sorted(batch) == sorted(takes) for batch in asked[:1]), (case, asked)
            assert again_words is None or again_words in asked[1][TAKE]["contents"][0]["parts"][-1]["text"], case
            viewed = json.loads((rows["finish-route-views"] / "views.json").read_text())[TAKE]
            laid_record = viewed["close_up_laid"]
            assert laid_record["laid"] == (laid == "views") and (
                not laid_record["laid"] or laid_record["fit"] >= route_cast.CLOSE_UP_FIT), (case, laid_record)
            parts_asked = asked[0][TAKE]["contents"][0]["parts"]
            assert len(parts_asked) == 2 * len(viewed["views"]) + past_views, (case, len(parts_asked))
            assert last_words is None or last_words in parts_asked[-1]["text"], case
            written = rows["finish-route-list"] / f"{TAKE}.json"
            assert written.exists() == (used is not None), case
            if used is not None:
                labels = json.loads(written.read_text())["labels"]
                assert {finish for regions in labels.values() for finish in regions.values()} == used, (case, labels)
            verdict = route_list.judge_list(rows["finish-route-list"], rows, {})
            assert verdict.answer == list_judged[0], (case, verdict)
            assert list_judged[1] is None or list(verdict.findings) == [list_judged[1]], (case, verdict)
            if split_judged is None:
                continue
            if laid == "split":
                rows = {**rows, **close_up_of(folder, rows[f"model {TAKE}"])}
            rows = split(folder, rows)
            worlds[case] = rows, asked
            answer_was, finding, counts = split_judged
            verdict = route_split.judge_split(rows["finish-route-split"], rows, {})
            assert verdict.answer == answer_was and (finding is None or finding in verdict.findings[0]), (case, verdict)
            record = json.loads((rows["finish-route-split"] / "split.json").read_text())[TAKE]
            if counts is None:
                assert record["fault"] and not (rows["finish-route-split"] / TAKE).exists(), (case, record)
                continue
            assert record["fault"] is None and record["unassigned"] == record["disagree"] == 0, (case, record)
            finish_of = np.load(rows["finish-route-split"] / TAKE / "finish.npy")
            mesh = route_split.model_of(rows["finish-route-views"] / TAKE)
            label_faces = (mesh.triangles_center[:, 0] < 0) & (mesh.face_normals[:, 2] > 0.9) & (laid == "views")
            assert (finish_of[label_faces] == 2).all() and (finish_of[~label_faces] != 2).all(), (case, finish_of)
            faces = np.load(rows["finish-route-views"] / TAKE / "faces.npz")["front"]
            seen_colours = np.load(rows["finish-route-views"] / TAKE / "colours.npz")["front"]
            reds = np.setdiff1d(faces[(faces >= 0) & (seen_colours == colours[0]).all(-1)], np.flatnonzero(label_faces))
            assert set(finish_of[reds]) == {0} and sorted(np.bincount(finish_of)) == counts, (case, finish_of)
            if parts is None:
                continue
            words, by, kept, unmeasured, texture_off, fault_count, fault_words = parts
            rows = parted(folder, rows)
            found = json.loads((rows["surfaces-parts"] / "parts.json").read_text())
            record = found["takes"][TAKE]
            assert record["method"] == "finish-route" and found["left_out"] == {}, (case, found)
            assert {row["words"] for row in record["parts"]} == words, (case, record["parts"])
            assert [finish["by"] for finish in record["finishes"]] == by, (case, record["finishes"])
            assert all(record["finishes"][index]["surface"] == surface for index, surface in kept.items()), case
            assert {finish["finish"] for finish in record["finishes"] if finish["measured_lab"] is None} == unmeasured, (
                case, record["finishes"])
            assert all(finish["delta_e"] <= finish_parts.COLOUR_DELTA_E for finish in record["finishes"]
                       if finish["by"] == "the list" and finish["finish"] not in unmeasured), (
                case, record["finishes"])
            assert record["colour_from"].startswith("close-up") == (laid is not None), (case, record["colour_from"])
            assert len(np.load(rows["surfaces-parts"] / TAKE / "parts.npy")) == 24, case
            assert surfaces.finish_parts.parts_faults(rows["surfaces-parts"]) == [], case
            assert route_parts.judge_parts(rows["surfaces-parts"], rows, {}).answer == "pass", case
            textured = route_parts.seen_colours(rows["finish-route-views"] / TAKE, finish_of.astype(int),
                                                len(record["finishes"]))
            assert all(np.linalg.norm(colour - finish_parts.library_lab(finish)) > finish_parts.COLOUR_DELTA_E
                       for colour, finish in zip(textured, record["finishes"])) == texture_off, (case, textured)
            if fault_count is not None:
                faults = close_up_judged(folder, record["finishes"])
                assert len(faults) == fault_count and all(fault_words in fault for fault in faults), (case, faults)
    # one batch asks every take, library first, each object its own seed, the list's wear taken only with a cause
    rows, asked = worlds["every finish labels its region, two takes in one batch"]
    body = asked[0][TAKE]
    assert "serviceTier" not in body  # its parts' count (two a view, then two) is the LISTED row's
    found = json.loads((rows["finish-route-list"] / f"{TAKE}.json").read_text())
    seed = route_list.take_seed(7, TAKE)
    assert seed != route_list.take_seed(7, OTHER)  # each object's wear and dirt pattern its own
    assert found["finishes"][0]["settings"] == {"token": "sign-red", "roughness": 1.0, "metal": 0.0, "seed": seed}
    assert found["finishes"][1]["settings"]["wear"] == 0.8 and found["finishes"][1]["settings"]["seed"] == seed + 1
    assert found["finishes"][1]["wear_cause"] == "walked path" and found["finishes"][0]["wear_level"] is None
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
    assert (worlds["the two boxes' batch ended: a gap named by the list"][0]["finish-route-list"]
            / f"{OTHER}.json").exists()  # the other take of the batch listed
    # a face takes the finish the views that see it most squarely give, a tie the finish round it (SPLIT_VOTES); views
    # disagreeing are recorded, never a gap, and unassigned area up to route_split.UNASSIGNED_MOST walks (SPLIT_SHARES)
    mesh = trimesh.creation.icosphere(subdivisions=3)
    apart = {"right": np.zeros(len(mesh.faces), dtype=int), "top": np.ones(len(mesh.faces), dtype=int)}
    votes = route_split.squared_votes(mesh, apart, route_split.cast.BASE, 2)
    for case, axis, view in SQUARED:
        assert (votes[np.abs(mesh.face_normals[:, axis]) > 0.9].argmax(1) == view).all(), case
    found = route_split.shares(mesh, apart, route_split.finish_parts.voted(apart, 2))
    assert found["disagree"] == 1.0 and route_split.split_fault(found) is None, found  # recorded, no gap
    for case, shares, fault in SPLIT_SHARES:
        judged = route_split.split_fault(shares)
        assert judged is None if fault is None else fault in judged, (case, judged)
    patch = np.linalg.norm(mesh.triangles_center - (0, 0, 1), axis=1) < 0.4
    assert mesh.area_faces[patch].sum() / mesh.area > 0.02  # over a stray's size, so only the tie decides it
    for case, picked, patched, finish in SPLIT_VOTES:
        voted = np.zeros((len(mesh.faces), 2))
        voted[:, 1] = 1.0  # finish 1 everywhere, so a tie read by argmax alone (finish 0) shows
        chosen = patch if picked == "patch" else np.arange(len(mesh.faces)) == 7
        voted[chosen] = patched
        assert (route_split.voted_finishes(mesh, voted, 2)[1][chosen] == finish).all(), case
    # a shell's inner wall no view sees takes the finish of the outer wall behind it, in its part (SPLIT_SHELL)
    tube = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(
        *(lambda made: (made.vertices, made.faces))(trimesh.creation.annulus(0.95, 1.0, 2.0, sections=48)), 0.2))
    radial = (tube.triangles_center[:, :2] * tube.face_normals[:, :2]).sum(1)
    upper = tube.triangles_center[:, 2] > 0
    walls = {"outer upper": (radial > 0.5) & upper, "inner upper": (radial < -0.5) & upper}
    voted = np.zeros((len(tube.faces), 2))
    voted[walls["outer upper"], 0] = 1.0
    voted[(np.abs(radial) <= 0.5) | ((radial > 0.5) & ~upper), 1] = 1.0  # the rims and the outer wall's lower half
    shell = dict(zip(("part", "finish"), route_split.voted_finishes(tube, voted, 2)))
    for case, wall, read, want in SPLIT_SHELL:
        found = {int(value) for value in shell[read][walls[wall]]}
        assert found == ({0} if want == "finish 0" else set(shell[read][walls["outer upper"]])), (case, found)
    # the keys the paint and bake rows take from the library, edit after edit to a copy of it
    hub_data(monkeypatch)
    data = a_copy()
    try:
        before = {row: keys(row, "hub", data) for row in ("surfaces-paint", "surfaces-bake")}
        for case, name, change, moves in KEY_MOVES:
            edit(data / "library" / name, change)
            now = {row: keys(row, "hub", data) for row in before}
            for row, moved in moves.items():
                assert (now[row] != before[row]) is moved, (case, row)
            before = now
    finally:
        shutil.rmtree(data)
    for row, place, by_part in LIBRARY_BY_PART:
        files = ROWS[row].files(place)
        assert isinstance(files["library"], tuple) is by_part and "places" not in files, (row, place)
        wide = getattr(ROWS[row].files, "wide", None) if by_part else True  # the parts read the library whole
        assert wide(place) if callable(wide) else wide, (row, place)
    # a bake row's model its data writes no entry for is a file that is never there, naming it; one written is none
    refused = library_reads.bake_refusals({"bake": {"models": {"bench_1": "bench-t1", "lost_1": "lost-t1"},
                                                    "entries": {"bench_1": {"size": [2.0, 0.9, 0.5]}}}},
                                          {"surfaces": "{home}/design/surfaces/hub.json"})
    assert list(refused) == ["bake entry lost_1"] and "no entry for lost_1" in refused["bake entry lost_1"], refused
    # the carry: an accepted record carries only from a committed tree, its code change proved a no-op for these
    # code versions, file by changed file; one whose record this store lacks is named, never read off None
    paint = ROWS["surfaces-paint"]
    for case, changes, why in WHY_NOT:
        assert carry.why_not(StubRunner(), paint, "hub", a_record(**changes), {}) == why, case
    orphan = StubRunner()
    orphan.store.accepted = lambda node: "a" * 64
    orphan.store.records = lambda node: []
    assert carry.standing(orphan, paint, "hub", {}) == \
        (None, f"its accepted output {'a' * 12} has no record in this store")
    record = a_record()
    changed = carry.changed_files(paint, record["commit"])
    assert changed
    (PROPS_HOME / "work").mkdir(parents=True, exist_ok=True)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="carry-proof-", dir=PROPS_HOME / "work"))
    try:
        full = {"made with code": "old code", "code now": carry.wide_code(paint),
                "no-ops": {name: "its change leaves the parts and surfaces as they were" for name in changed},
                "free rows": {}}
        for case, written, fault in PROOFS:
            (folder / "proof.json").write_text(json.dumps(written(full, changed)))
            assert carry.proof_fault(StubRunner(folder / "proof.json"), paint, record) == (
                fault and fault.format(changed=", ".join(changed))), case
    finally:
        shutil.rmtree(folder)
    # an accepted output kept over a key moved by an earlier output of the same content, by its row's content rule
    (PROPS_HOME / PICTURE).parent.mkdir(parents=True, exist_ok=True)
    (PROPS_HOME / PICTURE).write_bytes(b"the concept")
    try:
        for case, name, now_given, moved, differs, carries in CONTENT_KEPT:
            runner, row, record, keyed, now, foreseen = content_world(name, now_given, moved)
            place, part, read, node_read, _, _, rule = READS[name]
            node, why_text = graph.node_name(row, place), differs and differs.format(now=now[:12], home=PROPS_HOME)
            found, content, why = carry.changes_by_content(runner, row, place, keyed)
            assert why == why_text, (case, why)
            assert found == ((record, CHANGED) if differs is None else None), (case, found)
            assert differs is None or content is None, (case, content)
            hooked = carries is not None
            assert graph.Runner.same_earlier(runner, row, place, record, keyed) is (hooked and differs is None), case
            assert graph.Runner.same_earlier(runner, ROWS["surfaces-paint"], place, record, keyed) is False, case
            assert graph.Runner.same_earlier(runner, row, place, record, record) is True, case  # nothing moved
            if hooked:
                assert row.files.carries(runner, row, place, keyed) is carries, case
            if foreseen is not None:  # rebuy, foreseeing that remake, keeps it alike
                runner.foreseen = {node_read: foreseen}
                assert row.files.same_reads(runner, row, place, [node_read]) is (differs is None), case
            if differs is not None or (hooked and not carries):
                continue
            assert content == {read: {"from": record[part][read], "to": now, "rule": rule}}, (case, content)
            kept = row.files.carried(runner, row, place, keyed) if hooked else carry.kept_by_content(
                runner, row, place, keyed, record, "no-op-n", {"no-ops": {CHANGED[0]: "reads the same pictures"},
                                                               "same content": content})
            assert runner.store.record(node, keyed["key"]) == kept and kept["output"] == record["output"], case
            assert kept[part] == keyed[part] and kept["carried"]["same content"] == content, (case, kept)
    finally:
        shutil.rmtree(PROPS_HOME / PICTURE.rpartition("/")[0])
    # codes_at works the rows' code out at a commit: 548ab076 changed place_line.py alone (and its test), so the
    # paint's code moved from its parent and the parts' did not (a record carries only when made from the code at the
    # proof's commit); the two checkouts worked out side by side, each importing its whole stage table (about 3 s)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as pool:
        before, after = pool.map(carry.codes_at, ("548ab076^", "548ab076"))
    assert before["surfaces-paint"] != after["surfaces-paint"]
    assert before["surfaces-parts"] == after["surfaces-parts"]

    # A take stands square before it is laid (STAND_SQUARE), kept in the pose it was made in by one guard list (KEEPS_POSE),
    # its Pixal3D close-up deciding by outline, measured again as baked (SQUARE_AGAIN), and the check fails a tumbled
    # bake by name; the bake's outline is the likeness gate's. Each row's laid take is measured as check_step measures
    # a baked model (its `square` and `keeps_pose`), and `stands square` judges them all.
    import take_outline
    world = a_folder()
    bed_take = a_turned_take(world / "bed_square", rolled(40))
    bed_square = np.array(route_bake.stood_square({"bed_1": {"base": IDENTITY, "size": [2.0, 1.0, 0.6]}}, bed_take,
                                                  "bed_take", a_pose_world(world / "bed_world", BED))["bed_1"]["base"])
    closeups, baked = {}, {}
    for index, (case, row, model, take, roll, size, row_size, built, close_up, expected) in enumerate(STAND_SQUARE):
        labelled = a_turned_take(world / f"take{index}", rolled(roll), size=size)
        inputs = a_pose_world(world / f"place{index}", row)
        entry = {"base": IDENTITY, "size": row_size}
        if close_up is not None:
            points, triangles = route_bake.labelled_mesh(labelled)
            pose = np.eye(3) if close_up == "made" else bed_square.reshape(3, 3)
            mask = take_outline.silhouette(route_bake.fitted(points @ pose.T, row_size), triangles, 0, 15.0)
            middle = np.argwhere(mask).mean(axis=0).astype(int)
            mask[middle[0] - 4:middle[0] + 4, middle[1] - 4:middle[1] + 4] = False  # a hole the cut fills
            assert not mask[:4, :4].any()
            mask[:4, :4] = True  # a speck the cut drops
            inputs[route_bake.CLOSEUP] = closeups[close_up] = a_closeup(world / f"closeup{index}.png", mask)
        stood = route_bake.stood_square({model: entry}, labelled, take, inputs, built=built)
        stood = stood[model]
        kind, why = expected[0], (stood.get("stood") or {}).get("kept")
        laid = route_bake.labelled_points(labelled) @ np.array(stood["base"]).reshape(3, 3).T
        baked[f"{model} ({index})"] = {"square": dict(zip(("degrees", "loose"), tumble.measure(laid))),
                                       "keeps_pose": bake_check.keeps_pose_of(model, {"parts": take, **stood}, [row],
                                                                              inputs)}
        if kind == "square":
            assert tumble.measure(laid)[0] < 1.0 and np.allclose(np.ptp(laid, axis=0), expected[1], atol=0.02), (
                case, np.ptp(laid, axis=0))
            assert expected[2] is None or stood["stood"]["degrees"] > expected[2], (case, stood)
        elif kind in ("kept", "kept from"):
            assert stood["base"] == IDENTITY and (why == expected[1] if kind == "kept" else
                                                  why.startswith(expected[1])), (case, stood)
            left_out = bake_check.keeps_pose_of(model, {"parts": take, "stood": stood["stood"]}, [row], inputs)
            assert left_out.startswith(expected[1]), (case, left_out)
        elif kind == "same":
            assert stood == entry, (case, stood)
        else:
            outline = stood["stood"]["outline"]
            if kind == "outline kept":
                assert stood["base"] == IDENTITY and outline["made"] > outline["turned"], (case, stood)
                assert why == (f"turned square its outline against its close-up was {outline['turned']}, under its "
                               f"made pose's {outline['made']}: kept as made"), (case, stood)
            else:
                assert np.array(stood["base"]).tolist() == bed_square.tolist() and why is None, (case, stood)
                assert outline["turned"] >= outline["made"], (case, stood)
    rules = tumble.rules_of({"stance rules": REPO / "data/checks/stance.json",
                             "resting rules": REPO / "data/checks/resting.json"})
    for case, row, rows, expected in KEEPS_POSE:
        why = tumble.keeps_pose(row, rules, rows) if rows else tumble.keeps_pose(row, rules)
        assert (why is None if expected is None else bool(why) if expected is True else
                why == expected[1] if expected[0] == "is" else why.startswith(expected[1])), (case, why)
    # a model whose bake undid its own turn is left out by its `stood` alone, with no row of its own
    undone = {"parts": "valves_take", "stood": {"kept": "its turn left it 12.35 degrees off its frame as baked: kept "
                                                        "as made"}}
    assert bake_check.keeps_pose_of("pipe_valves_1", undone, [], a_pose_world(world / "valves", {})).startswith(
        "its turn left it 12.35"), undone
    # the Pixal3D close-up reaches the bake's card job listing
    files = [world / name for name in ("records.json", "claimed.json", "head.json")]
    files[2].write_text(json.dumps({"models": ["bed_1"]}))
    pixal = world / "home/work/pixal"
    (pixal / "bed_take.svviews").mkdir(parents=True)
    a_closeup(pixal / "bed_take.svviews/input.png", np.ones((4, 4), bool))
    with monkeypatch.context() as home:
        home.setattr(route_bake.prop_env, "PROPS_HOME", world / "home")
        job = json.loads(route_bake.card_job({"parts": world, "inventory here": world / "bed_world/handin.json"},
                                             world, "bed_take", (*files, world)).read_text())
    listing = json.loads(pathlib.Path(job["args"][0]).read_text())
    assert listing[route_bake.CLOSEUP] == str(pixal / "bed_take.svviews/input.png") in job["inputs"], listing
    degrees, loose = tumble.measure(UNSTEADY)
    assert degrees > tumble.DEGREES and loose < tumble.LOOSE, (degrees, loose)
    for case, entries, copies, measured, again_expected, after in SQUARE_AGAIN:
        measured = route_bake.SQUARE_ROUNDS if measured == "last" else measured
        found, again = route_bake.squared_again(copy.deepcopy(entries), copies, measured)
        assert again == again_expected, (case, again)
        for name, (base, kept) in after.items():
            turn = np.array(found[name]["base"]).reshape(3, 3)
            if base == "square":
                assert tumble.measure(copies[name] @ turn.T)[0] < 1.0, (case, name, found)
                assert found[name]["stood"]["made"] == IDENTITY, (case, found)
                assert found[name]["stood"]["baked"] == [list(tumble.measure(copies[name]))], (case, found)
                # its copy baked again as turned: square, so done, its turn kept
                done, again = route_bake.squared_again(found, {name: copies[name] @ turn.T}, measured + 1)
                assert again == [] and done[name]["base"] == found[name]["base"], (case, done)
                assert "kept" not in done[name]["stood"], (case, done)
            else:
                assert found[name]["base"] == (IDENTITY if base == "made" else entries[name]["base"]), (case, found)
            assert kept is None or found[name]["stood"]["kept"] == kept.format(degrees=degrees), (case, found)
    # `stands square` fails a baked model more than tumble.DEGREES off its frame (its frame box over tumble.LOOSE times
    # its own) by name with its angle (#36: base's module baked 32 degrees off and passed every gate); the rows above
    # stand square or keep their pose, a row whose design keeps its pose left out, said why
    (world / "square").mkdir()
    (world / "square/checks.json").write_text(json.dumps({
        "module_1": {"square": {"degrees": 32.06, "loose": 1.742}}, **baked}))
    found = bake_check.judge_square(world / "square", {}, None)
    kept = sorted(name for name, (*_, expected) in zip(baked, STAND_SQUARE) if expected[0] in KEPT_POSES)
    assert found.answer == checks.FAIL and found.measures["failing"] == 1, found
    assert found.findings == ("module_1: stands 32.1 degrees off its frame (its frame box 1.74 times its own)",
                              *(f"{name}: left out, {baked[name]['keeps_pose']}" for name in kept)), found.findings
    assert "rear_1 (1): left out, its design lays it lying (crashed)" in found.findings, found.findings
    # the bake's best outline is the gate's best of its YAWS ways (before the gate's fine search round it), and its cut
    # fills the close-ups' holes and drops their specks as pixal_cut does
    from score.stages.props import likeness, likeness_row
    trimesh.Trimesh(*route_bake.labelled_mesh(world / "take6")).export(world / "take.glb")
    points, triangles = likeness.gltf_mesh(world / "take.glb")
    for case, close_up, size in OUTLINE_SIZES:
        closeup = closeups[close_up]
        gate = likeness_row.whole_best_way(world / "take.glb", likeness_row.pixal_cut(closeup, world / "cuts", "take"),
                                           size)
        downs = take_outline.look_downs(size, take_outline.cut(closeup))
        assert gate["look_down"] in downs, (case, gate, downs)
        assert max(take_outline.best(points, triangles, take_outline.cut(closeup), down) for down in downs) == \
            max(gate["ways"]), (case, gate)
    # a moving door's holder bakes with its recess cut, a side wall and a back kept, the door clear in it (DOORS)
    holders_were = json.loads(json.dumps(DOOR_HOLDERS))
    for case, relations, holder, wanted, below, edges in DOORS:
        found = route_bake.recessed(DOOR_HOLDERS, holders.recesses(relations))
        assert DOOR_HOLDERS == holders_were, case  # the entries as they were
        assert all(entry["cuts"] == [] for model, entry in found.items() if model != holder), (case, found)
        [cut] = found[holder]["cuts"]
        assert cut == {"recess": wanted}, (case, cut)
        recess = next(relation["recess"] for relation in relations if "recess" in relation)
        axis, across = (0, 2) if recess["axis"] == "x" else (2, 0)
        size, (low, high) = DOOR_HOLDERS[holder]["size"], cut["recess"]
        assert -size[across] / 2 + route_bake.RECESS_BACK - 1e-9 <= low[across], (case, cut)  # a side wall each end
        assert high[across] <= size[across] / 2 - route_bake.RECESS_BACK + 1e-9, (case, cut)
        inner = low[axis] if recess["side"] > 0 else high[axis]
        assert recess["side"] * inner + size[axis] / 2 >= route_bake.RECESS_BACK - 1e-9, (case, cut)  # its back
        assert below is None or assembly_fitting.beside(recess, 0)[0] == pytest.approx(below), (case, recess)
        for along, bound, edge, least, most in edges:
            clear = edge - low[along] if bound == "low" else high[along] - edge
            assert clear >= least - 1e-9 and (most is None or clear <= most + 1e-9), (case, along, bound, clear)
    # the paint reads each take's finish turn off its final model and lays a raw take by it (PAINT_TURNS)
    turning = pathlib.Path(tempfile.mkdtemp())
    with prop_data.tools("props"):
        import glb_file
        import labels
        monkeypatch.setattr(labels, "PIXAL", turning)
        crate = trimesh.creation.box([0.6, 0.3, 0.2])
        crate.vertices[0] += [0.05, 0.02, 0.0]  # not symmetric: one turn only fits it
        crate.export(turning / "crate_1-5000.glb")
        raw = trimesh.creation.box([0.5, 0.87, 0.3])
        raw.vertices = (raw.vertices + [0.1, 0.0, 0.0]) @ STOOL_TILT.T @ labels.HALF_TURN.T  # off its middle
        raw.export(turning / "stool_1.glb")
        document, views = glb_file.read(turning / "stool_1.glb")
        document["asset"]["extras"] = {labels.FACING_KEY: "+Z"}
        glb_file.write(document, views, turning / "stool_1.glb")
        slimmed = raw.copy()
        slimmed.vertices = slimmed.vertices @ labels.HALF_TURN.T
        slimmed.export(turning / "stool_1-5000.glb")
        finished = {"crate_1": (crate, CRATE_TURN.T), "stool_1": (slimmed, STOOL_TILT)}  # the stool's tilt taken off
        for case, take, moved, turn, laid in PAINT_TURNS:
            final = finished[take][0].copy()
            final.vertices = finished[take][0].vertices @ finished[take][1] + [0.0, 0.0, moved]
            final.export(turning / f"{take}-final.glb")
            found = place_line.recovered_turn(turning, take)
            assert (found is None) if turn is None else np.allclose(found, turn, atol=1e-6), (case, found)
            if laid:
                matrix, _, bounds = place_line.finished_frame(raw, take)
                on = trimesh.transform_points(raw.vertices, matrix)
                assert np.allclose([on.min(0), on.max(0)], bounds, atol=0.01), (case, on.min(0), on.max(0), bounds)
    for case, marks, hit, placed, gaps in DECAL_MARKS:  # a listed mark placed on its part as a library decal (#164)
        found, missed = route_parts.decal_placements(marks, np.array([0, 1]), np.array([[0.0, 0.0, 1.0]] * 2),
                                                     hit, "close-up")
        assert [(row["decal"], row["part"], row["size"]) for row in found] == placed, (case, found)
        assert [row["why"] for row in missed] == gaps, (case, missed)
    marked = finish_ask.marks_of({"marks": [
        {"box_2d": [100, 200, 300, 600], "what": "label", "ink": "many", "on_finish": 1, "decal": "D1", "fits": True},
        {"box_2d": [0, 0, 10, 10], "what": "logo", "ink": "many", "on_finish": 1, "decal": "D2", "fits": True},
        {"box_2d": [0, 0, 10, 10], "what": "arrow", "ink": "one", "on_finish": 1, "decal": "D2", "fits": True},
        {"box_2d": [0, 0, 10, 10], "what": "badge", "ink": "one", "on_finish": 2, "decal": "D2", "fits": True}]},
        DECALS, 1, (1000, 500))
    assert [(mark["box"], mark["decal"], mark["gap"]) for mark in marked] == [
        ([200, 50, 400, 100], "surface/decal_label@1", None),
        ([0, 0, 10, 5], None, "its decal surface/decal_arrow@1 is one ink, the mark many"),
        ([0, 0, 10, 5], None, "a one-ink mark names no palette token for its ink")], marked
    with tempfile.TemporaryDirectory() as folder:  # the decals offered: the library's decals in force alone
        (pathlib.Path(folder) / "index").mkdir()
        (pathlib.Path(folder) / "index" / "surface.json").write_text(json.dumps({
            "schema": "score-lib-index/1", "kind": "surface", "entries": [
                {"address": "surface/decal_label@1", "state": "draft", "title": "label", "tags": {
                    "family": ["decal"], "class": ["paper"], "ink": ["many"], "size_m": ["0.200x0.100"],
                    "words": ["label"]}},
                {"address": "surface/decal_old@1", "state": "withdrawn", "title": "old", "tags": {"family": ["decal"]}},
                {"address": "surface/steel@1", "state": "draft", "title": "steel", "tags": {"family": ["image"]}}]}))
        assert decal_library.catalogue(folder) == DECALS[:1]
        assert decal_library.offered(DECALS, "plastic", "one") == DECALS[1:] and decal_library.catalogue(None) == []
    with pytest.raises(RuntimeError, match="decal_gone"):  # a decal the library does not hold stops the bake
        route_bake.decals_on([{"decal": "surface/decal_gone@1", "part": 0}], [{"part": 0, "surface": "paint"}], {},
                             lambda address: None)
    assert route_bake.decals_on([{"decal": "surface/decal_arrow@1", "part": 1, "ink_token": "sign-black"}],
                                [{"part": 1, "surface": "yellow_plastic"}], {"sign-black": (0.01, 0.01, 0.01)},
                                lambda address: pathlib.Path("/lib/decal.png")) == [
        {"decal": "surface/decal_arrow@1", "part": 1, "ink_token": "sign-black", "finish": "yellow_plastic",
         "image": "/lib/decal.png", "ink": [0.01, 0.01, 0.01]}]


def plane_cast(parts, scale=0.001):
    """A close-up cast onto the flat face z = 0 of the model's frame, a pixel `scale` metres: each probe's face by its
    place among the five probes (route_parts.PROBES' order: middle, left, right, top, bottom) from `parts`."""
    def cast(pixels):
        pixels = np.asarray(pixels, dtype=float)
        return np.array(parts), np.c_[pixels[:, 0] * scale, -pixels[:, 1] * scale, np.zeros(len(pixels))]
    return cast


# A printed mark on a take (#164): (case, its listed marks, the cast, the placements (decal, part, size in the take's
# frame) and the gaps' reasons). A 200 x 100 px label on part 0 at a millimetre a pixel is 0.2 x 0.1 m (its probes
# EDGE_IN inside its edges, grown back to them); a probe on another part is never used, so its size comes from the
# other side by the box's shape, and a mark both of whose sides reach another part is a gap: a decal never prints on
# another part's faces.
LABEL_MARK = {"box": [100, 100, 200, 100], "what": "label", "decal": "surface/decal_label@1", "ink": "many"}
DECAL_MARKS = [
    ("a mark the list names becomes a placement on its part at its cast size", [LABEL_MARK], plane_cast([0] * 5),
     [("surface/decal_label@1", 0, [0.2, 0.1])], []),
    ("a mark no library decal is, is a gap", [dict(LABEL_MARK, decal=None, gap="no library decal is this mark")],
     plane_cast([0] * 5), [], ["no library decal is this mark"]),
    ("its width reaching another part is sized by its height alone", [LABEL_MARK], plane_cast([0, 1, 1, 0, 0]),
     [("surface/decal_label@1", 0, [0.2, 0.1])], []),
    ("a mark reaching another part both ways is a gap, never printed there", [LABEL_MARK],
     plane_cast([0, 1, 1, 1, 1]), [], ["it spans more than its part 0"]),
    ("a mark whose middle misses the model is a gap", [LABEL_MARK], plane_cast([-1, 0, 0, 0, 0]), [],
     ["its box's middle is off the model"]),
]
DECALS = [{"address": "surface/decal_label@1", "class": "paper", "ink": "many", "size_m": [0.2, 0.1], "words": ["label"],
           "title": "label"},
          {"address": "surface/decal_arrow@1", "class": "plastic", "ink": "one", "size_m": [0.05, 0.05],
           "words": ["arrow"], "title": "arrow"}]


def baked_model(folder, name, mesh):
    """A baked .gltf of `mesh` in `folder/made`: its positions and triangles in one buffer, its .bin beside it."""
    points = np.asarray(mesh.vertices, dtype=np.float32).tobytes()
    corners = np.asarray(mesh.faces, dtype=np.uint32).tobytes()
    (folder / "made").mkdir(parents=True, exist_ok=True)
    (folder / "made" / f"{name}.bin").write_bytes(points + corners)
    (folder / "made" / f"{name}.gltf").write_text(json.dumps({
        "buffers": [{"uri": f"{name}.bin", "byteLength": len(points) + len(corners)}],
        "bufferViews": [{"buffer": 0, "byteLength": len(points)},
                        {"buffer": 0, "byteOffset": len(points), "byteLength": len(corners)}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(mesh.vertices), "type": "VEC3"},
                      {"bufferView": 1, "componentType": 5125, "count": mesh.faces.size, "type": "SCALAR"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}]}))


def tank_mesh(ends, height=1.6):
    """A tank's (vertices, faces), its own frame (+y up), on four corner legs ending `ends` up (the water tank's
    measured)."""
    body = trimesh.creation.box(bounds=((-0.7, 0.3, -0.7), (0.7, height, 0.7)))
    legs = [trimesh.creation.box(bounds=((across - 0.05, end, along - 0.05), (across + 0.05, 0.3, along + 0.05)))
            for (across, along), end in zip(((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)), ends)]
    mesh = trimesh.util.concatenate([body, *legs])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def fluid_shelves():
    """The garage's fluid shelves (2026-10-15): a shelf unit 1.0 tall in its own frame, its bottom shelf 0.06 up over
    four legs, one ending 0.02 up (4 cm)."""
    vertices, faces = tank_mesh((0.0, 0.0, 0.0, 0.02), height=1.0)
    vertices[vertices[:, 1] == 0.3, 1] = 0.06  # the body (and the legs' tops) down to a bottom shelf 0.06 up
    return vertices, faces


def fuel_tank():
    """The engine room's fuel tank (2026-10-15): an upright tank on two cradle feet, one 5.9 cm up, tipped onto it
    when dropped."""
    body = trimesh.creation.box(bounds=((-0.4, 0.3, -0.4), (0.4, 2.0, 0.4)))
    cradle = [trimesh.creation.box(bounds=((-0.5, end, along - 0.08), (0.5, 0.3, along + 0.08)))
              for along, end in ((-0.3, 0.0), (0.3, 0.059))]
    mesh = trimesh.util.concatenate([body, *cradle])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def garage_cabinet(rise):
    """The garage's control cabinet (2026-10-15): 1.5 m tall on a plinth rim whose underside rises `rise` across its
    0.6 m footprint under its floor's level cells (the quadrants and the cells' plane passed it)."""
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
    """The degrees the face a model rests on (its hull's face under its middle) leans off level."""
    mesh = trimesh.Trimesh(points, faces, process=False)
    middle = (mesh.triangles_center * mesh.area_faces[:, None]).sum(axis=0) / mesh.area
    hull = mesh.convex_hull
    hits, _, struck = hull.ray.intersects_location([[middle[0], 3.0, middle[2]]], [[0.0, -1.0, 0.0]])
    return np.degrees(np.arccos(-hull.face_normals[struck[np.argmin(hits[:, 1])]][1]))


# Takes levelled on their feet (place_line.levelled_feet): (case, its mesh, its standing height or None, what its record
# and points must show: "feet" found, how many "levelled", the "refused", the "far" side along z past which its points
# reach the floor, the "even" foot band its feet's lows then lie level in, whether it "rests" on a face brought level
# (True) or is left exactly as made (False)).
LEVELLED = [
    # in 15% of its height the shelf joins the legs into one foot and nothing is levelled
    ("fluid shelves in the wide band", fluid_shelves, None, {"feet": 1, "levelled": 0}),
    # capped at 10 cm through its standing height (0.05 here) the four legs are its feet, the short one brought down
    ("fluid shelves in the capped band", fluid_shelves, 2.0, {"feet": 4, "levelled": 1, "refused": []}),
    # two feet are levelled as three are: the short foot down on the floor
    ("a fuel tank on two cradle feet", fuel_tank, 2.0, {"feet": 2, "levelled": 1, "refused": [], "far": 0.2}),
    # the hangar's access stair (2026-10-15): two legs ending 29 and 33 cm up, outside the 10 cm band, levelled in the
    # whole band after the narrow one
    ("an access stair's legs over the narrow band", lambda: tank_mesh((0.0, 0.0, 0.12, 0.12), height=1.0), 2.0,
     {"levelled": 2, "refused": []}),
    # the water tank's three short legs are brought down before its bake, its four feet then level
    ("a water tank's short legs", lambda: tank_mesh((0.0, 0.022, 0.052, 0.127)), None,
     {"feet": 4, "levelled": 3, "refused": [], "even": 0.15 * 1.6}),
    # a leg 22 cm up is past what levelling may bring down: refused by its share of the tank's size, a missing leg
    ("a water tank's missing leg", lambda: tank_mesh((0.0, 0.0, 0.0, 0.22)), None,
     {"levelled": 0, "refused": [round(0.22 / max(1.6, 1.4 * 2 ** 0.5), 4)]}),
    # 1.2 cm across 0.6 m (under the 1.5 cm a share of its height lets pass) leans it over 1 degree: the face it rests
    # on comes down level; a cabinet on a level rim is left as made
    ("a tall cabinet's base step", lambda: garage_cabinet(0.012), None, {"rests": True}),
    ("a tall cabinet on a level rim", lambda: garage_cabinet(0.0), None, {"rests": False}),
]


def upright_seat():
    return trimesh.creation.box(bounds=((-0.3, 0.0, -0.3), (0.3, 1.0, 0.3)))


def tipped_seat():
    tipped = trimesh.creation.box(bounds=((-0.2, 0.0, -0.2), (0.2, 2.0, 0.2)))
    tipped.apply_transform(trimesh.transformations.rotation_matrix(math.radians(25.0), [0.0, 0.0, 1.0]))
    return tipped


# A take refused on its resting face alone (cockpit's pilot seat, 2026-11-12: its face rose 18.1% across its base while
# its weight lay inside what it touches); a flag refused on more.
SEAT = {"feet": 1, "gaps": [0.0], "levelled": [], "refused": [0.1807], "rests": 0.1807}
FLAG = {"feet": 1, "gaps": [0.0], "levelled": [], "refused": [0.1511, 0.2263], "rests": 0.2263}

# A painted take's feet judged (case, the judge: place_line's alone or the paint row's feet_stand reading the bake, the
# take, its feet record or the LEVELLED case whose record it is, its baked model or None, the verdict, a word its
# finding names or None): a seat refused on its resting face alone passes when its baked model stands by the resting
# check's measure, fails named when it does not, and every other refusal fails as a missing leg.
FEET_JUDGED = [
    ("a levelled tank passes", "place_line", "water_tank-r1", "a water tank's short legs", None, checks.PASS, None),
    ("a refused tank fails by name", "place_line", "water_tank-r1", "a water tank's missing leg", None, checks.FAIL,
     "water_tank-r1"),
    ("a seat resting upright passes", "feet_stand", "pilot_seat-r1", SEAT, upright_seat, checks.PASS, None),
    ("a tipped seat does not stand", "feet_stand", "pilot_seat-r1", SEAT, tipped_seat, checks.FAIL, "not stand"),
    ("a flag refused on more is a missing leg", "feet_stand", "pilot_seat-r1", FLAG, upright_seat, checks.FAIL,
     "missing leg"),
    ("no bake read: as refused", "feet_stand", "pilot_seat-r1", SEAT, None, checks.FAIL, "missing leg"),
]

# One inventory every standing question reads: the greenhouse's hand-in ({home}/design/props/<place>.json) rows, which
# name their take (`prop:<take>`) and stand on the floor the reading made a row of (`on:<floor row>`), beside the old
# inventories' rows the kinds alone name.
HAND_IN = [
    {"id": "floor_plates", "anchor": "ground", "size": [4.0, 5.0, 0.1], "thing": "prop:gh_floor_ab12"},
    {"id": "crate", "name": "crop crate", "anchor": "on:floor_plates", "thing": "prop:gh_crate_ab12"},
    {"id": "jar", "name": "seed jar", "anchor": "on:table", "thing": "prop:gh_jar_ab12"},
    {"id": "table", "name": "work table", "anchor": "floor", "size": [1.5, 0.8, 0.8], "thing": "prop:x"},
    {"id": "wall", "name": "left wall", "anchor": "on:floor_plates", "route": "shell", "thing": "prop:gh_wall_ab12"},
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
    {"id": "tin", "name": "tin", "anchor": "on:box", "thing": "prop:gh_tin_ab12"},
    {"id": "water_tank", "name": "water tank", "anchor": "floor", "thing": "prop:greenhouse_water_tank"},
    {"id": "cabinet", "anchor": "floor"},
    {"id": "glove", "name": "hanging glove", "anchor": "on:cabinet", "thing": "prop:lab_hanging_glove"},
    # a description's word is no class: the guard list reads a row's id and name
    {"id": "control_cabinet", "anchor": "floor", "thing": "prop:garage_control_cabinet", "name": "control cabinet",
     "description": "a standing steel control cabinet, cables running up from its top"},
    {"id": "control_stick", "anchor": "on:main_console", "thing": "prop:cockpit_control_stick",
     "name": "flight stick set in the console"},
    {"id": "cairn", "anchor": "floor", "thing": "prop:campgrounds_cairn",
     "name": "cairn of flat stones stacked into a narrow tower"},
    {"id": "small_panel", "anchor": "floor", "thing": "prop:wreck_small_panel", "name": "small torn hull panel",
     "leans": "debris lying tilted on purpose"},
    # #36, 2026-10-30: old_station's limp floor cables, levelled, fell from outline 0.637 to 0.207
    {"id": "cables", "anchor": "floor", "thing": "prop:old_station_cables", "name": "floor cables"},
    # the bay's own: the parts rack an old station's take claims, and a crane beside it
    {"id": "parts_rack", "name": "parts rack", "anchor": "floor"}, {"id": "crane", "anchor": "floor"},
]

# Whether a take stands on feet the paint levels (place_line.stands_on_feet over HAND_IN): (its entry, its take or None,
# stands).
STANDING = [
    ({"place": "greenhouse", "kind": "greenhouse_water_tank"}, None, True),
    ({"place": "lab", "kind": "lab_hanging_glove"}, None, False),  # held on its cabinet, but it hangs: no feet to level
    ({"place": "greenhouse", "kind": "gh_crate"}, None, False),  # by kind alone no designed row names it
    ({"place": "greenhouse", "kind": "gh_jar"}, "gh_jar_ab12", False),
    ({"place": "greenhouse", "kind": "gh_wall"}, "gh_wall_ab12", False),
    ({"place": "greenhouse", "kind": "gh_floor"}, "gh_floor_ab12", True),
    ({"place": "greenhouse", "kind": "gh_seat"}, "gh_seat_ab12", True),
    ({"place": "greenhouse", "kind": "gh_lamp"}, "gh_lamp_ab12", False),
    ({"place": "greenhouse", "kind": "gh_drum"}, "gh_drum_ab12", True),
    ({"place": "greenhouse", "kind": "gh_tin"}, "gh_tin_ab12", False),
    ({"kind": "garage_control_cabinet"}, None, True),
    ({"kind": "cockpit_control_stick"}, None, False),  # mounted on another object
    ({"kind": "campgrounds_cairn"}, None, False),  # a pile of stones
    ({"kind": "wreck_small_panel"}, None, False),  # debris lying tilted on purpose
    ({"kind": "old_station_cables"}, None, False),  # floor cables keep their pose
]

# A baked model's stance (bake_check.stance_lows): (case, its points, the highest foot's height, the tolerance).
STANCE_FEET = [(x, z) for x in (-0.5, 0.5) for z in (-0.3, 0.3)]
STANCES = [
    ("four feet on the floor", np.array([[x, 0.0, z] for x, z in STANCE_FEET] + [[0, 1.0, 0]]), 0.0, 0.0),
    # the hangar's parts rack stood on a middle part, its legs 22 cm up
    ("the parts rack's legs 22 cm up", np.array([[x, 0.22 if x > 0 else 0.0, z] for x, z in STANCE_FEET]
                                                + [[0, 1.0, 0]]), 0.22, 1e-6),
]

# Whether a baked model is held to stand (bake_check.stands): (its paint's feet labels, its row, stands); lying wreckage
# (a "torn" row) is left out, and so is a take whose paint levelled no feet.
STANDS = [
    ({"feet": 4}, "parts_rack_1", True),
    ({"feet": 4}, "leg_strut", False),
    ({"skipped": "no floor or held row lays its kind"}, "parts_rack_1", False),
]


def sloped_rack():
    """The hangar's parts rack: two legs ending 8% of its size over a middle part."""
    corners = [(x, z) for x in (-0.4, 0.4) for z in (-0.3, 0.3)]
    return np.array([[x, 0.08 if x > 0 else 0.0, z] for x, z in corners] + [[x, 0.5, z] for x, z in corners]
                    + [[0.0, 1.0, 0.0]])


def level_rack():
    rack = sloped_rack()
    rack[:4, 1] = 0.0
    return rack


def diamond_slab():
    slab = trimesh.creation.box(bounds=((-1.0, 0.0, -1.0), (1.0, 2.0, 1.0))).subdivide().subdivide().subdivide()
    slab.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 4, (0, 1, 0)))  # a diamond, as the hut's
    return np.asarray(slab.vertices).copy()


def guard_hut():
    """The square's guard hut: a slab base rising 8% of its size from one side to the other (8 cm up at its far
    corner, x = 1.41), each quadrant's lowest point by the middle."""
    hut = diamond_slab()
    bottom = hut[:, 1] < 1e-9
    hut[bottom, 1] += 0.08 * (hut[bottom, 0] + 2 ** 0.5) / 2 ** 1.5
    return hut


RACK_FEET = lambda base: np.arange(len(base)) < 4  # noqa: E731  (the rack's four corners low)
RACK_OVER = lambda base: np.arange(len(base)) >= 4  # noqa: E731
HUT_BOTTOM = lambda base: base[:, 1] < 0.081  # noqa: E731  (its base, up to its 8 cm rise)
HUT_OVER = lambda base: base[:, 1] > 0.5  # noqa: E731

# A base brought down level as one piece (place_line.flattened_base: points, band, tolerance, most) or as one plane
# through its middle (place_line.sloped_base: points, band, cell, tolerance, most): (case, its points, the step, its
# arguments, what its record and points must show: "flattened" and "refused" as listed, its "rise" (None: none found;
# a number: within 1 cm of it; a case: refused at that case's rise), "quadrants" all lower than, the points "down"
# under 1e-9 (or 1 cm for a slab), those "kept" as made, or "as made" all, and nothing brought down past its
# "above lowest" point).
BASES = [
    ("a rack's far legs come down", sloped_rack, "flattened", (0.25, 0.01, 0.15),
     {"flattened": [0.08, 0.08], "down": (RACK_FEET, 1e-9), "kept": RACK_OVER}),
    ("a far gap is refused", sloped_rack, "flattened", (0.25, 0.01, 0.05), {"refused": [0.08, 0.08], "as made": True}),
    ("a level rack is left", level_rack, "flattened", (0.25, 0.01, 0.15), {"flattened": []}),
    # the blind spot: each quadrant's lowest lies at x = 0, so the quadrants find nothing
    ("a hut's quadrants", guard_hut, "flattened", (0.5, 0.03, 0.4), {"quadrants": 0.05}),
    ("a hut slopes as one plane", guard_hut, "sloped", (0.5, 0.17, 0.03, 0.4),
     {"rise": 0.08, "refused": [], "down": (HUT_BOTTOM, 0.01), "kept": HUT_OVER, "above lowest": True}),
    ("a hut's slope past the most", guard_hut, "sloped", (0.5, 0.17, 0.03, 0.05),
     {"rise": "a hut slopes as one plane"}),
    ("a level slab", diamond_slab, "sloped", (0.5, 0.17, 0.03, 0.4), {"rise": None}),
    ("a round bottom", lambda: np.asarray(trimesh.creation.icosphere(4).vertices), "sloped", (0.5, 0.17, 0.03, 0.4),
     {"rise": None, "as made": True}),
]

# The bake's paint (base_level.py, run by inside/paint_fit.py) counts a base level within 3 cm through the standing
# height, as the feet are: a hundredth of base's large hangar (0.84 m) left corners 34 to 60 cm up and "stands level"
# failed it (2026-11-12). (a hall's corner raised, its standing height, whether base_level moves it): a hall 2 units
# tall stood 20 m (a hundredth 1.4 m): its corner 8 cm up comes down, 2 cm up stays; stood 0.2 m (a hundredth 1.4 cm,
# under 3 cm) it levels exactly as before.
HALLS = [(0.008, 20.0, True), (0.002, 20.0, False), (0.3, 0.2, False), (0.1, 0.2, False)]


def on_three_legs():
    """A body 2 by 4 from 0.3 to 1.5 up on three 0.2 wide legs from the floor at x, z (-0.8, -1.5), (0.8, -1.5) and
    (0.8, 1.5): the quadrant at x < 0, z > 0 holds no leg, its underside 0.3 up."""
    body = trimesh.creation.box(bounds=((-1.0, 0.3, -2.0), (1.0, 1.5, 2.0))).subdivide().subdivide()
    legs = [trimesh.creation.box(bounds=((x - 0.1, 0.0, z - 0.1), (x + 0.1, 0.3, z + 0.1))).subdivide()
            for x, z in ((-0.8, -1.5), (0.8, -1.5), (0.8, 1.5))]
    return trimesh.util.concatenate([body, *legs])


# The rise along z of on_its_floor's wheels' plane (1.7 degrees off level).
FLOOR_RISE = 0.03
# (case, on_its_floor's leg bottom and whether its body leans with its wheels, whether the bake's paint turns it onto
# its wheels' plane): a lone leg 0.11 under the plane's lowest wheel (0.21 under the plane where it stands) is cut; one
# ending on the plane makes five feet on one leaning plane, none lone; a level body over wheels on a leaning plane
# keeps its own up (hangar's control desk front).
FLOORS = [("a lone leg under the plane its body and four wheels lean on", -0.1, True, True),
          ("five feet on one leaning plane", 0.05 + FLOOR_RISE * 1.9, True, False),
          ("a level body over four wheels on a leaning plane", -0.1, False, False)]


def on_its_floor(leg, leaning):
    """A body 2 by 4 from 0.5 to 1.3 up on four wheels (radius 0.3, across x) whose bottoms lie on the plane
    y = 0.05 + FLOOR_RISE z, the body leaning with them when `leaning` (else level), and a 0.1 wide leg at z 1.9 from
    `leg` up into the body; the mesh, each wheel's vertex indices and the leg's."""
    tilt = trimesh.transformations.rotation_matrix(-math.atan(FLOOR_RISE), [1, 0, 0])
    body = trimesh.creation.box(bounds=((-1.0, 0.5, -2.0), (1.0, 1.3, 2.0))).subdivide()
    if leaning:
        body.apply_transform(tilt)
    parts, wheels, start = [body], [], len(body.vertices)
    for x, z in ((-1.1, -1.2), (1.1, -1.2), (-1.1, 1.2), (1.1, 1.2)):
        wheel = trimesh.creation.cylinder(radius=0.3, height=0.2, sections=48)
        wheel.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 0, 1]))
        wheel.apply_translation([x, 0.35, z])
        wheel.apply_transform(tilt)
        parts.append(wheel)
        wheels.append(np.arange(start, start + len(wheel.vertices)))
        start += len(wheel.vertices)
    strut = trimesh.creation.box(bounds=((-0.05, leg, 1.85), (0.05, 0.7, 1.95))).subdivide().subdivide()
    parts.append(strut)
    return trimesh.util.concatenate(parts), wheels, np.arange(start, start + len(strut.vertices))


# A sloping plane the paint brought down before is brought down as before (capped alone, its cells' 2 cm of unevenness
# lie off a 5 mm plane and it found none); one rising 2 cm, under the hundredth, now comes down too: (its rise, its
# cells' roughness, whether base_level's capped plane finds a rise).
CAPPED_PLANES = [(0.08, 0.02, True), (0.02, 0.0, True), (0.002, 0.0, False)]


# Bakes held to their surface (bake_check.on_surface): (case, its baked Lab, the surface's clean Lab, the place's dirt
# Lab or None, its dirt, the surface's bare Lab or None, the place's wear, "<" or ">" and the bound the distance keeps).
WHITE, REGOLITH = [89.6, -1.7, 1.6], [56.8, 0.2, 3.1]
YELLOW, BARE, SOOT = [80.5, 3.5, 78.8], [66.3, -1.1, -4.5], [13.2, 3.7, 5.9]
WORN_SIX_TENTHS = [clean + 0.6 * (bare - clean) for clean, bare in zip(YELLOW, BARE)]
BAKED_TRIM = [73.2, 2.2, 41.3]
DELTA = bake_check.BAKE_DELTA_E
ON_SURFACE = [
    # the wreck: dirt 0.6 in regolith (L* 56.8); its white hull (89.6) bakes to 69.0 and is on its surface
    ("the wreck's white hull dirtied", [69.0, -0.8, -3.2], WHITE, REGOLITH, 0.6, None, 0.0, "<", 6),
    ("the same white at a clean place", [69.0, -0.8, -3.2], WHITE, REGOLITH, 0.0, None, 0.0, ">", DELTA),
    ("baked darker than its dirt reaches", [40.0, 0, 0], WHITE, REGOLITH, 0.6, None, 0.0, ">", DELTA),
    ("dirt with no dirt colour", [69.0, -0.8, -3.2], WHITE, None, 0.6, None, 0.0, ">", DELTA),
    # the engine room, worn 0.8, dirt 0.5: its power core's hazard trim 20.1 off its clean yellow, part worn to steel
    ("the engine room's hazard trim worn", BAKED_TRIM, YELLOW, SOOT, 0.5, BARE, 0.8, "<", 6),
    ("the hazard trim unworn", BAKED_TRIM, YELLOW, SOOT, 0.5, BARE, 0.0, ">", DELTA),
    ("the hazard trim with no bare colour", BAKED_TRIM, YELLOW, SOOT, 0.5, None, 0.0, ">", DELTA),
    ("the hazard trim held to a wrong surface", BAKED_TRIM, [19.2, -0.7, -3.2], SOOT, 0.5, BARE, 0.8, ">", DELTA),
    # wear has causes (the paper, Appendix D) and passes only toward the bare colour, only as far as the place's wear
    ("worn through to bare in a place worn 0.4", BARE, YELLOW, None, 0.0, BARE, 0.4, ">", DELTA),
    ("darkened toward black however worn", [50.0, 3.5, 78.8], YELLOW, None, 0.0, BARE, 0.8, ">", DELTA),
    ("worn where the surface has no bare colour", WORN_SIX_TENTHS, YELLOW, None, 0.0, None, 0.8, ">", DELTA),
    ("worn in a place with no wear", WORN_SIX_TENTHS, YELLOW, None, 0.0, BARE, 0.0, ">", DELTA),
    ("worn 0.6 toward bare in a place worn 0.8", WORN_SIX_TENTHS, YELLOW, None, 0.0, BARE, 0.8, "<", 1),
]

# Lab's junction_box_1, bake of 2026-10-14: 56% of its crane_yellow_paint's area baked yellow, 15% between, 29% the grey
# panel at the same L*. A part's baked colour is each channel's own area median: (case, the areas, the median).
DARKER, BETWEEN, GREY, LIGHTER = [62.0, 2.0, 38.0], [62.9, 0.5, 17.0], [63.5, -0.7, -4.4], [65.0, 2.0, 38.0]
JUNCTION_BOX = np.array([DARKER] * 28 + [BETWEEN] * 15 + [GREY] * 29 + [LIGHTER] * 28)
AREA_MEDIANS = [
    ("every triangle the same area: the yellow the bake wrote", np.ones(100), [63.5, 2.0, 38.0]),
    ("only the grey panel's triangles have area", np.array([0.0] * 43 + [1.0] * 29 + [0.0] * 28), GREY),
]

# Loose islands merged (finish_parts.merged_islands): (case, its pieces as (box extents, its centre, its finish), how
# many parts there are, the pieces that end as one part of finish 1). A crumb stripe is 4 cm, beside a 1 m box.
CRUMBS = [((0.04,) * 3, (0.6, -0.3 + 0.2 * number, 0), 1) for number in range(4)]
HOST = ((1, 1, 1), (0, 0, 0), 0)
MERGED = [
    ("a loose bit joins the nearest larger island of its own finish",
     [HOST, ((0.02,) * 3, (0.53, 0, 0), 1), ((1, 1, 1), (3, 0, 0), 1)], 2, [1, 2]),
    ("a finish of crumbs only keeps them as one part however small", [HOST, *CRUMBS], 2, [1, 2, 3, 4]),
    ("one crumb alone keeps its finish as a part of its own", [HOST, CRUMBS[0]], 2, [1]),
]

# A finish the cleaning left (finish_parts.kept_finishes): (case, the labels before, after, the face areas, kept).
KEPT = [
    ("a finish left with an island of its size stays as the cleaning left it", [0, 1, 2, 2], [0, 0, 0, 2], [1.0] * 4,
     [0, 1, 0, 2]),
    # engineroom desk's paper label (#36)
    ("a finish left only a face of no area gets its faces back", [0, 1, 1, 0], [0, 0, 1, 0], [1.0, 1.0, 0.0, 1.0],
     [0, 1, 1, 0]),
]

# Patchy paint on the shared sphere and a loose 5 cm box 3 m off it (finish_parts.without_strays): astronaut-made-s1,
# 2026-10-23, where the walk left jagged islands of the dark joints over its fabric (stray 0.054). A stray joins the
# finish it borders; a finish with no island of its own size keeps its islands, unless they cover that size together
# (the cooktop's specks, #36): then its largest island and each island over ISLAND_LEAST (a screen of the hub's right
# console, likeness@hub 2026-11-06) stand for it and the rest are strays. A whole piece keeps its finish, and a small
# piece of mixed finishes joins its largest island. Each row lays (mark, finish) over a sphere of finish 0 in order:
# (case, laid, the marks every face of which ends in that finish, the marks no face of which does, the one mark
# outside which no face moves, the finish whose largest island alone is left, fewer faces than the mark painted it,
# and what the cleaning does to patchy.py's stray: "drops" and passes, or "passes").
LAID_BASE = [("under", 1), ("patch", 1), ("lone", 2), ("loose", 1)]
STRAYS = [
    ("a blotch joins the finish round it, a finish nowhere larger keeps its island, a whole piece its finish",
     LAID_BASE, [("patch", 0), ("lone", 2), ("loose", 1)], [], "patch", None, "drops"),
    ("a finish in specks only, each under STRAY_ISLAND and over it together (camp kitchen_counter_2's cooktop)",
     LAID_BASE + [("specks", 2)], [], [], None, (2, "specks"), "passes"),
    ("islands over ISLAND_LEAST stand (the hub's right console's screens); specks no screen's island holds go",
     LAID_BASE + [("specks", 2), ("screens", 2)], [("screens", 2)], [("apart", 2)], None, None, None),
    ("two small islands, small together too, keep their finish (portholes)",
     LAID_BASE + [("portholes", 3)], [("portholes", 3)], [], None, None, None),
    ("a small piece of two finishes joins its largest island", LAID_BASE + [("piece", 0)], [("loose", 1)], [], None,
     None, None),
]

# The screens' cleaning made parts (finish_parts.merged_islands) and judged (patchiness): (case, laid over the
# cleaned screens, the marks whose faces end in at most `most` parts, most, the stray: "passes", "as alone" (the
# first row's), or "under a screen" (above 0, under the smallest screen's share)). Base's glazing held loose glass
# bits; old_station's tape and foil held crumbs.
PARTED = [
    ("the screens alone stand as parts", [], [], None, "passes"),
    ("a loose bit of screen is taken into a screen's part: that screen is no blotch", [("loose", 2)],
     ["loose", "screens"], 4, "as alone"),
    ("a crumb of screen in the paint is taken into a screen's part too", [("crumb", 2)], ["crumb", "screens"], 4,
     "under a screen"),
]

# Six blotches of finish 1 over 3% of the sphere in all (finish_parts.patchiness): islands of a detail finish (its
# family or words: decals, stickers, labels, notes, fittings, rubber) are parts of their own as a lone fitting is
# (old_station solar_panel_mast, 2026-10-28: its steel fittings, gathered by merged_islands into one part of several
# islands, read stray 0.032); the same blotches of a body finish fail as patchy paint. (case, the two finishes, the
# blotches one part with the paint or one part of their own, passes.)
BODY_PAINT = {"finish": "white paint", "parts": "the body", "family": "paint"}
HULL_PAINT = {"finish": "white paint", "parts": "the hull", "family": "paint"}
FITTINGS = {"finish": "bare steel fittings", "parts": "clamps and collars", "family": "steel"}
CASTERS = {"finish": "black", "parts": "caster wheels", "family": "rubber"}
BLOTCHES = [
    ("a body finish's blotches in the paint's part", [BODY_PAINT, BODY_PAINT], "with the paint", False),
    ("a body finish's blotches as one part of their own", [HULL_PAINT, HULL_PAINT], "of their own", False),
    ("steel fittings' islands as one part", [HULL_PAINT, FITTINGS], "of their own", True),
    ("rubber casters' islands as one part", [HULL_PAINT, CASTERS], "of their own", True),
]

# Finishes judged against each other (finish_parts.out_of_order): L* 60 and 70 greys; the campgrounds' power unit's
# white measured 80.6 on the darker grey. A finish route's finish paints in its own colour while it keeps its listed
# surface (astronaut-made, 2026-10-23: its white shell in suit-white). (case, the lighter-listed, the other, out of
# order.)
GREYS = {"anodized_natural": {"colour": [0.2843] * 3}, "dust_coated_paint": {"colour": [0.4075] * 3}}
POWER_WHITE = {"surface": "anodized_natural", "measured_lab": [80.6, 1.0, 2.0]}
DUSTY = {"surface": "dust_coated_paint", "measured_lab": [69.7, 0, 0]}
SHELL = dict(POWER_WHITE, colour=[0.9131] * 3, listed_surface="anodized_natural")
FABRIC = dict(DUSTY, colour=[0.4075] * 3, listed_surface="dust_coated_paint")
OUT_OF_ORDER = [
    ("a white measured lighter on the darker surface", POWER_WHITE, DUSTY, True),
    ("the same pair the other way round", DUSTY, POWER_WHITE, False),
    ("a finish with no measure", POWER_WHITE, dict(DUSTY, measured_lab=None), False),
    ("a finish route's shell in its own colour on its listed surface", SHELL, FABRIC, False),
    ("a finish route's shell moved off its listed surface: the library's colour", dict(SHELL, listed_surface="other"),
     FABRIC, True),
]


# A finish is see-through by its listed surface's family (finish_parts.see_through). (case, the finish, see-through.)
SURFACE_FAMILIES = {"red_plastic": {"family": "plastic"}, "cast_steel": {"family": "steel"},
                    "glass": {"family": "glass"}}
SEE_THROUGH = [
    ("a lamp dome of red transparent plastic",
     {"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"}, True),
    ("a polished reflector", {"finish": "Polished reflective metal", "parts": "internal reflector",
                              "surface": "cast_steel"}, False),
    ("a grey painted housing", {"finish": "Grey painted steel", "parts": "housing", "surface": "cast_steel"}, False),
]

# A place's surface data against its bake specs (place_line.unwalked): a place nobody walks (the wreck's did) bakes
# with kicks 0; data that says nothing hands its specs back as given, the very same object (recipes.WALKED: kicked as
# before, 2026-10-13). (case, the surface data, the kicks every spec says, or None: the specs themselves.)
SPECS = {"dark_panel": {"recipe": "painted_metal"}, "bare_steel": {"recipe": "bare_metal"}}
UNWALKED = [
    ("a place nobody walks", {"foot_traffic": False}, {0.0}),
    ("data that says nothing of walking", {"place": "hub"}, None),
]

# A batch job runs on its one priced class; no stock is a gap, never another class (#21).
RENTED = ["CLASSES", "PAINT_CLASSES"]


# Finishes held to their colour (finish_parts.checked_finishes): a finish off its colour takes the nearest surface of
# its family, or the room's kit surface, only where that keeps the list's meaning (the audit of 2026-11-04): its recipe
# (a handrail never takes the floor's grating, rusted steel never clean hull paint), its glow, and its hue (gold foil
# never silver, a blue decal never grey frame paint). As the row makes it (parts_kept held), a kit surface further from
# the close-up than the list's own never takes it over (shiplock's dark locker interior, 2026-11-11), a picked finish
# keeps its pick (the engine room's crate, 2026-11-13) and is never moved by the order, and a glow in a family of the
# scene library's coining ("energy": the engine room's core seen white-hot, 2026-11-13) is judged by its own colour.
# Glass off the lit colour keeps its surface (owner, #8); the beacon's red transparent dome measured pale pink on its
# brighter half keeps red_plastic, an opaque grey plastic that far off moves, an opaque red one is off its colour.
CHAIR = {"vinyl_seat": {"family": "plastic", "colour": [0.03, 0.06, 0.10]},
         "grey_plastic": {"family": "plastic", "colour": [0.35, 0.35, 0.35]},
         "dark_panel": {"family": "steel", "colour": [0.01, 0.01, 0.01]}}
LIGHT_GREY = finish_parts.library_lab(CHAIR["grey_plastic"]) + np.array([3.0, 0, 0])
GREY_STEEL = {"finish": "grey steel", "parts": "body", "surface": "dark_panel", "fits": True}
STEELWORK = {"bare_steel": {"family": "steel", "recipe": "bare_metal", "colour": [0.30, 0.30, 0.31]},
             "deck_grate": {"family": "steel", "recipe": "perforated_metal", "colour": [0.30, 0.30, 0.31]},
             "deck_plate": {"family": "steel", "recipe": "bare_metal", "colour": [0.31, 0.31, 0.32]},
             "rusted_steel": {"family": "steel", "recipe": "rusted_metal", "colour": [0.25, 0.08, 0.03]},
             "hull_panel": {"family": "steel", "recipe": "painted_metal", "colour": [0.26, 0.10, 0.05]},
             "blue_decal": {"family": "paint", "recipe": "painted_metal", "colour": [0.02, 0.06, 0.30]},
             "seam_paint": {"family": "paint", "recipe": "painted_metal", "colour": [0.05, 0.05, 0.05]},
             "gold_foil": {"family": "foil", "recipe": "anodized", "colour": [0.60, 0.40, 0.05]},
             "silver_foil": {"family": "foil", "recipe": "anodized", "colour": [0.20, 0.20, 0.20]}}
SEEN_STEEL = {name: finish_parts.library_lab(spec) for name, spec in STEELWORK.items()}
KIT = ["deck_grate", "hull_panel", "seam_paint", "deck_plate"]
HANDRAIL = {"finish": "steel handrail", "parts": "rails", "surface": "bare_steel", "fits": True}
BRUSHED = {"finish": "brushed steel", "parts": "frame", "surface": "bare_steel", "fits": True}
WALKWAY = [HANDRAIL, {"finish": "rusted riveted steel", "parts": "tube", "surface": "rusted_steel", "fits": True},
           {"finish": "blue decal", "parts": "decal", "surface": "blue_decal", "fits": True}]
SHELF_PAIR = {"dark_steel": {"family": "steel", "recipe": "bare_metal", "colour": [0.043] * 3},
              "light_steel": {"family": "steel", "recipe": "bare_metal", "colour": [0.29] * 3}}
SHELF_FRAME = {"finish": "worn steel frame", "parts": "frame", "surface": "dark_steel", "fits": True, "picked": {}}
STEEL_BOX = {"finish": "steel box", "parts": "box", "surface": "light_steel", "fits": True}
# dark at L* 25, light at 61: the frame seen lighter than the box
SEEN_PAIR = [finish_parts.library_lab(SHELF_PAIR["dark_steel"]) + [20.0, 0, 0],
             finish_parts.library_lab(SHELF_PAIR["dark_steel"]) + [7.0, 0, 0]]
CORE = {"core_glow": {"family": "energy", "recipe": "glowing", "colour": [0.07, 0.33, 1.0]}}
COLUMN = {"finish": "Blue core glow", "parts": "column", "surface": "core_glow", "fits": True}
REACTOR = {"reactor_glow": {"family": "glass", "recipe": "glowing", "colour": [0.10, 0.45, 1.0]},
           "side_glazing": {"family": "glass", "recipe": "glass", "colour": [0.005, 0.0225, 0.05]}}
# the water tank's: its panel 13 L* lighter than its steel in the close-up, painted_panel under bare_steel here
TANK_LIBRARY = {"painted_panel": {"family": "painted", "colour": [0.30, 0.31, 0.33]},
                "cream_paint": {"family": "painted", "colour": [0.55, 0.53, 0.46]},
                "bare_steel": {"family": "steel", "colour": [0.35, 0.36, 0.38]},
                "glass": {"family": "glass", "colour": [0.6, 0.65, 0.7]}}
BEACON_LIBRARY = {"red_plastic": {"family": "plastic", "colour": [0.45, 0.02, 0.01]},
                  "plastic_grey": {"family": "plastic", "colour": [0.33, 0.31, 0.27]}}
PALE = np.array([70.8, 21.2, 11.5])
ABSENT = object()


class Words(str):
    """An expected text the found one holds somewhere in it."""


# (case, the take, its finishes, their measured L*a*b*, the library, the room's kit or None, parts_kept held, what each
# found finish holds: {field (dotted reaches in): value}).
CHECKED = [
    ("grey vinyl takes the nearest plastic by colour, grey steel far off its black is off its colour",
     {"kind": "lab_chair", "object": "desk chair"},
     [{"finish": "grey vinyl", "parts": "seat", "surface": "vinyl_seat", "fits": True}, GREY_STEEL],
     [LIGHT_GREY, LIGHT_GREY], CHAIR, None, False,
     [{"surface": "grey_plastic", "by": "nearest of its family by colour"},
      {"surface": "dark_panel", "by": "off its colour", "fits": False,
       "new_surface.lab": [round(float(value), 1) for value in LIGHT_GREY]}]),
    ("a finish in its own token's colour is held to that colour, not its surface's",
     {"kind": "lab_chair", "object": "desk chair"}, [dict(GREY_STEEL, colour=[0.35, 0.35, 0.35])], [LIGHT_GREY], CHAIR,
     None, False, [{"surface": "dark_panel", "by": "the list"}]),
    ("a handrail never takes the grating, rust never the hull paint, a blue decal seen black never the seam paint",
     {"kind": "walkway", "object": "walkway"}, WALKWAY,
     [SEEN_STEEL["deck_grate"], SEEN_STEEL["hull_panel"], SEEN_STEEL["seam_paint"]],
     {name: spec for name, spec in STEELWORK.items() if name != "deck_plate"}, KIT[:3], False,
     [{"surface": "bare_steel"}, {"surface": "rusted_steel"}, {"surface": "blue_decal", "by": "off its colour"}]),
    ("brushed steel seen as the room's deck plate takes it", {"kind": "module", "object": "module"}, [BRUSHED],
     [SEEN_STEEL["deck_plate"]], STEELWORK, KIT, False,
     [{"surface": "deck_plate", "by": "the room's kit surface by colour"}]),
    ("gold foil seen silver is off its colour, never silver foil", {"kind": "module", "object": "module"},
     [{"finish": "gold MLI foil", "parts": "module", "surface": "gold_foil", "fits": True}],
     [SEEN_STEEL["silver_foil"]], STEELWORK, KIT, False, [{"surface": "gold_foil", "by": "off its colour"}]),
    ("as the row makes it, a kit surface further than the list's own never takes it over",
     {"kind": "module", "object": "module"}, [BRUSHED], [SEEN_STEEL["bare_steel"] + [-3.0, 0.0, 0.0]], STEELWORK, KIT,
     True, [{"surface": "bare_steel", "by": "the list"}]),
    ("as the row makes it, brushed steel seen as the deck plate still takes it", {"kind": "module", "object": "module"},
     [BRUSHED], [SEEN_STEEL["deck_plate"]], STEELWORK, KIT, True,
     [{"surface": "deck_plate", "by": "the room's kit surface by colour"}]),
    ("as the row makes it, a picked finish keeps its pick, never the kit's", {"kind": "module", "object": "module"},
     [dict(BRUSHED, picked={"token": "steel-grey"})], [SEEN_STEEL["deck_plate"]], STEELWORK, KIT, True,
     [{"surface": "bare_steel", "by": "the list"}]),
    ("unheld, the order moves a frame seen lighter than its box", {"kind": "shelf", "object": "shelf"},
     [SHELF_FRAME, STEEL_BOX], SEEN_PAIR, SHELF_PAIR, None, False, [{"surface": "light_steel"}, {}]),
    ("as the row makes it, the order never moves a pick: the other finish moves", {"kind": "shelf", "object": "shelf"},
     [dict(SHELF_FRAME, picked={"token": "slate"}), STEEL_BOX], SEEN_PAIR, SHELF_PAIR, None, True,
     [{"surface": "dark_steel"}, {"surface": "dark_steel"}]),
    ("unheld, a glow of a coined family seen white-hot is off its colour", {"kind": "core", "object": "core"},
     [COLUMN], [np.array([77.1, 0.7, -2.7])], CORE, None, False, [{"by": "off its colour"}]),
    ("as the row makes it, a glow of a coined family is judged by its own colour", {"kind": "core", "object": "core"},
     [COLUMN], [np.array([77.1, 0.7, -2.7])], CORE, None, True, [{"by": "its own colour", "surface": "core_glow"}]),
    ("a glow seen as glass never takes the glass", {"kind": "reactor", "object": "reactor"},
     [{"finish": "blue reactor tube", "parts": "tube", "surface": "reactor_glow", "fits": True}],
     [finish_parts.library_lab(REACTOR["side_glazing"])], REACTOR, None, False,
     [{"surface": "reactor_glow", "by": "its own colour"}]),
    ("glass off the lit colour keeps its surface, judged by its own colour and no cover",
     {"kind": "lamp", "object": "lamp"}, [{"finish": "red lit lens", "parts": "lens", "surface": "glass"}],
     [np.array([45.0, 60.0, 40.0])], TANK_LIBRARY, None, False,
     [{"surface": "glass", "by": "its own colour", "cover": ABSENT}]),
    ("the beacon's see-through dome keeps red against its highlights, an opaque grey moves, an opaque red is off",
     {"kind": "beacon", "object": "beacon"},
     [{"finish": "Red transparent plastic", "parts": "lamp dome", "surface": "red_plastic"},
      {"finish": "Grey plastic", "parts": "knob", "surface": "red_plastic"},
      {"finish": "Red plastic", "parts": "knob", "surface": "red_plastic"}], [PALE, PALE, PALE], BEACON_LIBRARY, None,
     False, [{"surface": "red_plastic", "by": "its own colour", "cover": True},
             {"surface": "plastic_grey", "by": "nearest of its family by colour"},
             {"surface": "red_plastic", "by": "off its colour"}]),
]

# Finishes kept in their close-up's lightness order (finish_parts.in_close_up_order): (case, the object, its finishes,
# the library, what each found finish holds, or None: it comes back as given). The hangar's parts shelving: its grey
# plastic bins 27.7 L* over its steel in the close-up, plastic_grey 1.5 under galvanized_steel in the library; the
# steel, seen at L* 42, takes cast_steel, nearer its close-up colour; with none nearer, the order stays as it was.
TANK_PANEL = [round(float(value), 1) for value in finish_parts.library_lab(TANK_LIBRARY["cream_paint"]) - [4, 0, 0]]
TANK_STEEL = [round(float(value), 1) for value in finish_parts.library_lab(TANK_LIBRARY["bare_steel"]) - [8, 0, 0]]
TANK = [{"finish": "off-white paint", "surface": "painted_panel", "measured_lab": TANK_PANEL, "by": "the list"},
        {"finish": "steel legs", "surface": "bare_steel", "measured_lab": TANK_STEEL, "by": "the list"}]
SHELF_LIBRARY = {"galvanized_steel": {"family": "steel", "colour": [0.328, 0.361, 0.397]},
                 "plastic_grey": {"family": "plastic", "colour": [0.386, 0.332, 0.258]},
                 "cast_steel": {"family": "steel", "colour": [0.070, 0.084, 0.102]}}
SHELVING = [{"finish": "Grey steel", "surface": "galvanized_steel", "measured_lab": [41.9, 0.6, -0.6], "by": "the list"},
            {"finish": "Light grey plastic", "surface": "plastic_grey", "measured_lab": [69.6, 0.2, 0.9],
             "by": "named again (its material)"}]
IN_ORDER = [
    ("the water tank's paint takes cream, keeping the close-up's order", "water tank", TANK, TANK_LIBRARY,
     [{"surface": "cream_paint", "by": "nearest of its family in order"}, {}]),
    ("with no cream the paint is off its colour, lighter than its steel", "water tank", TANK,
     {name: spec for name, spec in TANK_LIBRARY.items() if name != "cream_paint"},
     [{"by": "off its colour", "new_surface.why": Words("lighter than bare_steel")}, {}]),
    ("one finish has nothing to order", "x", TANK[1:], TANK_LIBRARY, [None]),
    ("steel a little out of order takes a nearer surface of its family", "parts shelving", SHELVING, SHELF_LIBRARY,
     [{"surface": "cast_steel", "by": "nearest of its family in order"},
      {"surface": "plastic_grey", "by": "named again (its material)"}]),
    ("with no surface nearer the order stays as it was", "parts shelving",
     [dict(SHELVING[0], measured_lab=[66.0, -1.0, -4.0]), dict(SHELVING[1], measured_lab=[80.0, 0.0, 0.0])],
     SHELF_LIBRARY, [None, None]),
]

# The list's meaning (finish_parts.meaning_faults, the gate "kept the list's meaning"): a finish moved off its recipe,
# glow or hue, and a take whose largest finish moved off its row name's colour (the hangar's thick red cables as
# black_hose), unless another finish's own words name that colour; where the finishes of the row's own thing word exist
# they, not the largest, hold its colour (base's 'green plants' dome, its frame the largest part, its 'plant leaves'
# green: passes; with no plant finish, or its plants painted grey: fails). (case, the take, its record made from the
# cables' record, the words each fault holds.)
CABLE_PARTS = [{"judge": "deck_grate", "words": "steel handrail", "share": 0.7},
               {"judge": "deck_plate", "words": "brushed steel", "share": 0.3}]
LATTICE_PAINT = {"recipe": "painted_metal", "lab": [60.9, 0.6, 10.9]}
LEAF = {"recipe": "rubber", "lab": [40.9, -26.8, 25.5]}
LATTICE = {"finish": "greenhouse frame lattice", "parts": "dome lattice ribs", "surface": "seam_trim_dark",
           "listed_surface": "greenhouse_lattice", "by": "the room's kit surface by colour",
           "looks": {"listed": LATTICE_PAINT, "painted": dict(LATTICE_PAINT, lab=[36.4, 0.5, 5.4])}}
LEAVES = {"finish": "plant leaves", "parts": "plants growing inside the dome", "surface": "plant_leaves",
          "listed_surface": "plant_leaves", "by": "the list", "looks": {"listed": LEAF, "painted": LEAF}}
GREEN_DOME = {"object": "green plants", "finishes": [LATTICE, LEAVES],
              "parts": [{"judge": "seam_trim_dark", "words": "greenhouse frame lattice", "share": 0.53},
                        {"judge": "plant_leaves", "words": "plant leaves", "share": 0.003}]}
MEANING = [
    ("a handrail moved to the grating, red cables painted steel", "walkway-t1", lambda cables: cables,
     [("steel handrail",), ("thick red cables",)]),
    ("a cable sheath's own words claim the red", "walkway-t1", lambda cables: dict(cables, finishes=[
        *cables["finishes"], {"finish": "cable sheath", "parts": "the red cables on the floor",
                              "surface": "seam_paint"}]), [("steel handrail",)]),
    ("a steel walkway of brushed steel on the deck plate", "walkway-t1",
     lambda cables: dict(cables, object="steel walkway", finishes=cables["finishes"][1:]), []),
    ("the dome's plants, not its frame, carry the row's green", "dome-t1", lambda cables: GREEN_DOME, []),
    ("a dome with no plant finish: its frame never holds the green", "dome-t1",
     lambda cables: dict(GREEN_DOME, finishes=[LATTICE]), [("'green plants' names green",)]),
    ("a dome whose plants are painted grey", "dome-t1", lambda cables: dict(GREEN_DOME, finishes=[LATTICE, dict(
        LEAVES, surface="seam_trim_dark", by="the room's kit surface by colour",
        looks={"listed": LEAF, "painted": dict(LATTICE_PAINT, lab=[36.4, 0.5, 5.4])})]),
     [(), ("'green plants' names green",)]),
]

# A light built in code (route_parts.lit_take): (case, the take, its build's size, lit). A stem lamp's post is a post.
LIT_TAKES = [
    ("a wall light's bar", {"kind": "light", "object": "wall light"}, [1.0, 0.1, 0.1], True),
    ("wall pipes the same size", {"kind": "pipe", "object": "wall pipes"}, [1.0, 0.1, 0.1], False),
    ("a street light's post", {"kind": "light", "object": "street light"}, [0.3, 0.3, 6.0], False),
]
# A lit take's finishes (route_parts.lit_finishes) take the glowing surface nearest their colour: (case, its finishes,
# the library, parts_kept held, what each found finish holds, or None: as given). A light bar listed as its glass tube
# and its metal end caps: the tube glows, the caps keep their own surface (airlock's wall lamp, 2026-10-29); a strip
# lamp's diffuser in plastic on a glowing surface glows and its steel housing keeps its steel, as the row makes it
# (shiplock's lights, 2026-11-11: housings painted as the blue screen), held only while it runs.
LIGHTS = {"warm": {"recipe": "glowing", "colour": [1.0, 0.8, 0.3]},
          "cold": {"recipe": "glowing", "colour": [0.3, 0.6, 1.0]},
          "steel": {"recipe": "bare_metal", "colour": [0.5, 0.5, 0.5]}}
LIGHT_BAR = {"finish": "light bar", "surface": "steel", "fits": True, "by": "the list",
             "measured_lab": [float(value) for value in finish_parts.library_lab(LIGHTS["cold"])]}
DIFFUSER = dict(LIGHT_BAR, finish="white diffuser", family="plastic", surface="warm")
HOUSING = dict(LIGHT_BAR, finish="dark metal housing", family="steel")
LIT = [
    ("a light bar takes the glowing surface nearest its colour", [LIGHT_BAR], LIGHTS, False,
     [{"surface": "cold", "fits": True, "by": "its light, built in code"}]),
    ("with no glowing surface it is flagged", [LIGHT_BAR], {"steel": LIGHTS["steel"]}, False,
     [{"fits": False, "new_surface.why": Words("no glowing surface")}]),
    ("its glass tube glows, its metal end caps keep their surface",
     [dict(LIGHT_BAR, family="glass"), dict(LIGHT_BAR, finish="metal end caps", family="steel")], LIGHTS, False,
     [{"surface": "cold"}, None]),
    ("as the row makes it, a plastic diffuser glows, its steel housing kept", [DIFFUSER, HOUSING], LIGHTS, True,
     [{"surface": "cold", "family": "plastic"}, None]),
    ("unheld, the housing glows too", [DIFFUSER, HOUSING], LIGHTS, False, [{}, {"surface": "cold"}]),
]


def unlike(found, given, expected):
    """Where `found` finishes differ from `expected` ({field: value}, a dotted field reaching in, Words a text held; None:
    as `given`): (index, field, found value) of each difference."""
    differ = []
    for index, (finish, before, want) in enumerate(zip(found, given, expected, strict=True)):
        if want is None:
            differ += [] if finish == before else [(index, "as given", finish)]
            continue
        for field, value in want.items():
            got = finish
            for step in field.split("."):
                got = got.get(step, ABSENT) if isinstance(got, dict) else ABSENT
            if isinstance(value, Words):
                held = isinstance(got, str) and value in got
            else:
                held = got is value if value is ABSENT or isinstance(value, bool) else got == value
            differ += [] if held else [(index, field, got)]
    return differ


def squares(*layouts):
    """One 1 m square a layout (its four corners' texture coordinates, glTF's v down), side by side in x."""
    corners = [[[x + left, 0.0, z] for x, z in ((0, 0), (1, 0), (1, 1), (0, 1))]
               for left, _ in zip(itertools.count(2), layouts)]
    return {"positions": np.array(corners, dtype=float).reshape(-1, 3),
            "uvs": np.array(layouts, dtype=float).reshape(-1, 2),
            "triangles": np.array([[base + 0, base + 1, base + 2] if half == 0 else [base + 0, base + 2, base + 3]
                                   for base in range(0, 4 * len(layouts), 4) for half in (0, 1)]),
            "maps": np.zeros(2 * len(layouts), dtype=int)}


def laid_square(low_u, low_v, wide, tall):
    """A square's corners laid as the bake winds them: x along u, z up the picture."""
    return [[low_u, low_v + tall], [low_u + wide, low_v + tall], [low_u + wide, low_v], [low_u, low_v]]


# #92, the texture layout the bake wrote (uv_layout.py): a sound pair of 1 m squares in a 1024 x 1024 picture and a
# third square beside it: (case, the third square, the one fault it is named by, None: sound). The sparse one is the
# bake's old hidden share, a face given a twentieth of the density (bake.py HIDDEN_SHARE); the stretched one is
# twice uv_layout.STRETCH long (its height filled in by the test, the constant read there).
SOUND = [laid_square(0.1, 0.1, 0.3, 0.3), laid_square(0.1, 0.5, 0.3, 0.3)]
LAYOUTS = [
    ("sound", laid_square(0.5, 0.1, 0.3, 0.3), None),
    ("mirrored", list(reversed(laid_square(0.5, 0.1, 0.3, 0.3))), "mirrored"),
    ("overlap", laid_square(0.2, 0.2, 0.3, 0.3), "overlap"),
    ("stretched", None, "stretched"),
    ("sparse", laid_square(0.5, 0.1, 0.3 * 0.05, 0.3 * 0.05), "sparse"),
    ("outside", laid_square(0.8, 0.1, 0.3, 0.3), "outside"),
]
THIN_SPECK = laid_square(0.5, 0.5, 0.0005, 0.0005)  # a third of the charts too thin (and a speck of the density)

# The bake lays a failing layout again before it bakes (inside/layout_fit.py, 2026-11-12): (case, the measured
# layout, its side, the cap, the unfolding round, the next step: None keeps it as laid, "UNFOLD" projects the folded
# faces again, a number is the side doubled). "passing" is the wreck's open hatch (0.64% shared, its unfolding thinned
# it): a layout the check passes is never unfolded again, only a thin one doubled.
NEXT_STEPS = [
    ("a sound layout is kept as made", "sound", 512, 2048, 0, None),
    ("a fold is projected again", "overlap", 512, 2048, 0, "UNFOLD"),
    ("a round that shared no fewer stops it", "overlap", 512, 2048, None, None),
    ("a passing but thin layout gets twice the side", "passing", 512, 2048, 0, 1024),
    ("a passing layout neither thin is kept", "passing, not thin", 512, 2048, 0, None),
    ("a passing layout's later round still unfolds", "passing, not thin", 512, 2048, 1, "UNFOLD"),
    ("a thin layout gets twice the side", "thin", 512, 2048, 0, 1024),
    ("a thin layout at the cap stays", "thin", 2048, 2048, 0, None),
]

# Which part a baked triangle is named by (bake_check.baked_surfaces): (case, the world, whether it is named by the
# texel the bake wrote, the parts it names). The bowl: the flat's bowl stack, bake of 2026-10-13; its glass rim's
# sliver lies under the texel whose centre the bake took on its enamel neighbour, so the check samples that texel
# from that point, as the bake did (its glass had failed at dE 66.6 while the bake was right). The tower: far_city's
# pencil tower, 2026-10-13, its cut-down copy 0.6 m proud of the facade; beside a post, the post's side lies nearer
# than the facade the bake's ray meets (the nearest part named post_dark, dE 45); the ray inward names the facade, a
# triangle over the post the post.
RAY_NAMED = [
    ("the bowl's triangles by their middles", "bowl", False, ["enamel_white", "glass"]),
    ("the bowl's triangles by the texel the bake wrote", "bowl", True, ["enamel_white", "enamel_white"]),
    ("the tower's triangles by the bake's ray", "tower", False, ["facade_paint", "post_dark"]),
]
RAY_WORLDS = {
    "bowl": ({"enamel_white": [[-1.0, 0.0, -0.05], [0.0, 1.0, 0.05]], "glass": [[0.0, 0.0, -0.05], [1.0, 1.0, 0.05]]},
             None,
             # one large triangle over the enamel covering texel (0, 0)'s centre in a 2 x 2 texture, one sliver over
             # the glass whose middle falls in that texel but not on its centre
             {"positions": np.array([[-0.9, 0.1, 0.05], [-0.1, 0.1, 0.05], [-0.5, 0.9, 0.05],
                                     [0.4, 0.4, 0.05], [0.6, 0.4, 0.05], [0.5, 0.6, 0.05]]),
              "uvs": np.array([[0.2, 0.0], [0.5, 0.0], [0.2, 0.45], [0.05, 0.05], [0.12, 0.05], [0.05, 0.12]]),
              "triangles": np.array([[0, 1, 2], [3, 4, 5]]), "maps": np.array([0, 0])},
             {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [2.0, 1.0, 0.1]}),
    "tower": ({"facade_paint": [[-5.0, 0.0, -1.0], [5.0, 2.0, 0.0]], "post_dark": [[-0.05, 0.0, 0.0], [0.05, 2.0, 1.0]]},
              0.1,
              {"positions": np.array([[0.3, 0.9, 0.6], [0.5, 0.9, 0.6], [0.4, 1.1, 0.6],
                                      [-0.1, 0.9, 1.6], [0.1, 0.9, 1.6], [0.0, 1.1, 1.6]]),
               "triangles": np.array([[0, 1, 2], [3, 4, 5]])},
              {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [10.0, 2.0, 2.0]}),
}


# --- library_reads and carry ---

def a_copy():
    """data/library copied into a folder of its own: the data folder."""
    (PROPS_HOME / "work").mkdir(parents=True, exist_ok=True)
    data = pathlib.Path(tempfile.mkdtemp(prefix="library-reads-", dir=PROPS_HOME / "work"))
    shutil.copytree(REPO / "data/library", data / "library")
    return data


def hub_data(monkeypatch):
    """The hub's surface data of the test's own, in a folder of its own: one crate take, baked."""
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "hub.json").write_text(json.dumps({"place": "hub", "library": "hub", "takes": {
        "crate-t1": {"place": "hub", "kind": "crate", "object": "a crate", "library_places": ["hub"]}},
        "bake": {"models": {"crate_1": "crate-t1"}, "entries": {"crate_1": {"size": [1.0, 1.0, 1.0]}}}}))
    for data in (surfaces.data, surface_data):
        monkeypatch.setattr(data, "FOLDER", folder)


def keys(row, place, data):
    return text_hash(ROWS[row].files(place)["library"][1](data / "library"))


def edit(path, change):
    found = json.loads(path.read_text()) if path.exists() else {}  # details.json: none since the old kinds' retired
    change(found)
    path.write_text(json.dumps(found, indent=1))


# The hub's library keys as one edit after another to the copied library moves them: (case, the library file, its
# edit, {row: whether its key moves}). The paint paints the surfaces its records name; the bake's job, written from git
# (bake_job.py), carries every variant of the library as its specs, so a variant added anywhere moves every bake; a
# kind's details move the paint.
KEY_MOVES = [
    ("a surface variant added anywhere", "materials.json",
     lambda library: library["families"].setdefault("painted", {"variants": {}})["variants"].update(
         brand_new_panel={"recipe": "painted_metal", "token": "hull-trim", "bare": "hull"}),
     {"surfaces-paint": False, "surfaces-bake": True}),
    ("the hub's one take's kind's details", "details.json",
     lambda details: details.setdefault("crate", {}).update(wall=0.123), {"surfaces-paint": True}),
]

# Which rows key the library by part (a tuple of the wide read and the part), each with a wide twin, and none keyed on
# place json: (row, place, keyed by part). surfaces-names left the line, so the parts read the library whole.
LIBRARY_BY_PART = [
    ("surfaces-paint", "hub", True),
    ("surfaces-bake", "hub", True),
    ("surfaces-paint", "people", True),
    ("surfaces-parts", "hub", False),
]


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


# Why the paint's accepted record does not carry (carry.why_not): (case, the record's changes, why).
WHY_NOT = [
    ("made from a tree with changes not committed", {"uncommitted": True},
     "made from a tree with changes not committed"),
    ("its code changed with no proof", {}, "its code changed since, with no proof its result is the same"),
]

# A proof of the paint's code change (carry.proof_fault): (case, the proof as written from the full one and the files
# changed since the record's commit, its fault, {changed} those files). The full one names every changed file a no-op
# for these code versions.
PROOFS = [
    ("every changed file named a no-op", lambda full, changed: full, None),
    ("its no-ops say nothing", lambda full, changed: {**full, "no-ops": {name: "" for name in changed}},
     "its proof does not say why these changes leave the result as it is: {changed}"),
    ("for other code versions", lambda full, changed: {**full, "code now": "another code"},
     "its proof is for other code versions"),
]

PICTURE = "work/carry-content/hub.png"  # a concept picture under PROPS_HOME, written as b"the concept"
FROZEN = "frozen/20261031-021736-1.home/" + PICTURE  # the same picture's path into a run's frozen home
LOOK = "people-look-parts-"  # the first row of a look's parts
FROZEN_GLTF = ("/home/someone/.score/frozen/20261110-101556-1.home/store/cache/checkouts/" + "b" * 64
               + "/made/astronaut-made.gltf")


def props_inputs_output(store, key, given):
    """A props-inputs@hub output whose one row names given["concept"] (a path under PROPS_HOME, made absolute when it
    names the frozen home), recorded under `key` as read from a picture of given["sha"]'s text hash ("" for no hash);
    (its output, None)."""
    folder = pathlib.Path(tempfile.mkdtemp())
    concept = str(PROPS_HOME / given["concept"]) if given["concept"].startswith("frozen/") else given["concept"]
    row = {"id": "desk", "scene": "hub", "view": "v1", "concept": concept, "drawn": None, "layer": "objects"}
    (folder / "rows.json").write_text(json.dumps({"rows": [row], "not_in_inventory": []}))
    (folder / "contract.json").write_text("{}")
    output = store.put_tree(folder)
    store.write_record("props-inputs@hub", key, {"output": output, "files": {
        "view v1": text_hash(given["sha"]) if given["sha"] else ""}, "finished": "2026-11-04T00:00"})
    return output, None


def plan_output(store, key, given):
    """A plan@hub output (its plan.json: the hub's floor, one item, `given` over them) recorded under `key`; (its
    output, its plan.json as a foreseen remake hands it)."""
    plan = {"place": "hub", "floor": [[0, 0], [6, 4]], "floor_height": 0.0, "walls": {"high": 3.0},
            "items": [{"name": "LAMP 1", "box": [0, 0, 1, 1]}], **given}
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "plan.json").write_text(json.dumps(plan))
    output = store.put_tree(folder)
    store.write_record("plan@hub", key, {"output": output, "finished": "2026-11-07T00:00"})
    return output, {"plan.json": plan}


def people_made_output(store, key, given):
    """A people-made@people output handing on one look baked as given["model"], its labelled take given["labelled"],
    recorded under `key`; (its output, None)."""
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "labelled").mkdir()
    (folder / "labelled" / "astronaut-made-s1.npz").write_bytes(given["labelled"])
    (folder / "made.json").write_text(json.dumps({"astronaut-made": {
        "take": "astronaut-made-s1", "model": given["model"], "labelled": "labelled/astronaut-made-s1.npz"}}))
    output = store.put_tree(folder)
    store.write_record("people-made@people", key, {"output": output, "finished": "2026-11-10T00:00"})
    return output, None


# Each reading row's earlier output, by the content rule it reads it with: (place, its key part, the input's name in
# it, the node that made it, its maker, what its accepted output was made from, the rule).
READS = {
    "closeup": ("hub", "after", "props-inputs", "props-inputs@hub", props_inputs_output,
                {"concept": FROZEN, "sha": "the concept"}, "score.stages.props.same_content.props_inputs"),
    "rough-align": ("hub", "after", "plan", "plan@hub", plan_output, {},
                    "score.stages.rough_model.same_content.plan_floor"),
    LOOK: (None, "beside", "people-made@people", "people-made@people", people_made_output,
           {"model": FROZEN_GLTF, "labelled": b"the painted take"}, "score.stages.people.same_content.people_made"),
}

# An accepted output whose key moved by an earlier output (and maybe another key part) kept by content alone, or not
# (carry.changes_by_content; a row with content hooks by its carries, carried, same_reads and same_earlier): (case,
# the reading row, the earlier output now, another key part moved, why the content differs or None, whether it
# carries, None for a row with no content hook, kept only through a proof). {now} is the new output's first 12,
# {home} PROPS_HOME. A closeup whose props-inputs moved by path text alone (655e0465, #75: an absolute path into a
# run's frozen home, now relative to PROPS_HOME) is kept; rough-align reads its plan's place, floor and heights alone
# (the square, 2026-11-07); a look's parts read people-made beside by its content (2026-11-10: the 9 accepted
# look-parts, about EUR 15, re-keyed by a model path into a run's frozen home).
CONTENT_KEPT = [
    ("a closeup whose props-inputs moved by path text alone", "closeup", {"concept": PICTURE, "sha": "the concept"},
     {}, None, None),
    ("a closeup whose picture really changed", "closeup", {"concept": PICTURE, "sha": "another concept"}, {},
     "props-inputs's output holds other content (rows.json)", None),
    ("a closeup whose picture's path resolves to no file", "closeup",
     {"concept": "design/nowhere/hub.png", "sha": "the concept"}, {},
     "props-inputs's output {now}: row desk's concept design/nowhere/hub.png resolves to no file "
     "({home}/design/nowhere/hub.png)", None),
    ("a closeup whose new record holds no hash, never read off the disk", "closeup",
     {"concept": PICTURE, "sha": ""}, {}, "props-inputs's output {now}: row desk's concept: its record holds no hash "
     "for view v1", None),
    ("a plan redrawn without an item", "rough-align", {"items": []}, {}, None, True),
    ("a plan with another floor", "rough-align", {"floor": [[0, 0], [7, 4]]}, {},
     "plan's output holds other content (floor)", False),
    ("a plan redrawn without an item, the key's seed moved too", "rough-align", {"items": []}, {"seed": 1}, None,
     False),
    ("a people-made moved by its model path alone", LOOK,
     {"model": "made/astronaut-made.gltf", "labelled": b"the painted take"}, {}, None, True),
    ("a people-made whose labelled take is other bytes", LOOK,
     {"model": "made/astronaut-made.gltf", "labelled": b"another painted take"}, {},
     "people-made@people's output holds other content (files)", False),
    ("a people-made moved by its model path alone, the key's params moved too", LOOK,
     {"model": "made/astronaut-made.gltf", "labelled": b"the painted take"}, {"params": {"take": "another"}}, None,
     False),
]
CHANGED = ["score/stages/props/closeup_row.py"]  # the repository files changes_since names


class ContentRunner(StubRunner):
    """A runner over `store` whose changes_since names CHANGED while the earlier outputs are the record's."""
    def __init__(self, store, record):
        super().__init__()
        self.store, self.record = store, record

    def changes_since(self, stage, place, keyed):
        same = all(keyed.get(part) == self.record.get(part) for part in ("after", "beside"))
        return (self.record, CHANGED) if same else None


def content_world(name, now_given, moved):
    """A store of its own holding `name`'s accepted output made from READS' earlier output, and the earlier output
    `now_given` makes; (its runner, the reading row, the accepted record, the moved key, the new output, its
    foreseen remake)."""
    place, part, read, node_read, made, then_given, _ = READS[name]
    row = ROWS[name] if name in ROWS else next(row for each, row in ROWS.items() if each.startswith(name))
    node = graph.node_name(row, place)
    store = a_store()
    then, _ = made(store, "k-then", then_given)
    record = {**a_record(), "node": node, part: {read: then}, "finished": "2026-11-04T00:00"}
    store.write_record(node, record["key"], record)
    store.write_accept(node, {"output": record["output"], "key": record["key"], "at": "2026-11-04T00:00"})
    now, foreseen = made(store, "k-now", now_given)
    keyed = {**record, "key": "n" * 64, part: {read: now}, **moved}
    return ContentRunner(store, record), row, record, keyed, now, foreseen


# --- route ---

RED, BLUE = (200, 30, 30), (150, 120, 220)  # each near its finish's token (sign-red, bay-three)


TAKE, OTHER = "two_boxes-t1", "other-t1"


# The views row's verdict (route_views.make_views, judge_views) on the two boxes' place, by the takes its object filter
# keeps: (case, the takes, the verdict, the start of its first finding, None for a pass).
VIEWS_JUDGED = [
    ("the two boxes' take seen on every side", [TAKE], "pass", None),
    ("a take whose raw model the inputs lack", [OTHER], "fail", f"{OTHER}: no raw take"),
    ("a filter that keeps none of the place's takes", ["no-such-take"], "fail", "cockpit: no take to work on"),
]

# A take's seen share judged against what any angle reaches (route_views.take_faults): area inside the model, out of
# every angle, is no miss (astronaut-made-s1: 49.5% reachable, all of it seen); views seeing under SEEN_LEAST of what
# any angle sees still are. (case, seen share, reachable share, faulted.)
SEEN = [
    ("everything any angle reaches seen", 0.495, 0.495, False),
    ("under SEEN_LEAST of what the angles reach seen", 0.2, 0.495, True),
]


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


def cast_views(folder, takes=(TAKE,), labelled_close_up=False):
    """The views row's make on the two boxes (each take named the same model), the object filter keeping `takes`;
    the inputs carry the scene palette, and with `labelled_close_up` the two boxes' own close-up and camera with the
    GREEN label (close_up_of). Made once a module for the same takes, model and close-up (VIEWS_MADE), copied after."""
    views = folder / "views"
    model = two_boxes(folder)
    inputs = {"surfaces": place_data(folder), "finish-route-palette": paletted(folder),
              "surface-library": libraried(folder), **{f"model {take}": model for take in takes},
              **(close_up_of(folder, model, label=True) if labelled_close_up else {})}
    made = VIEWS_MADE.get((takes, model.read_bytes(), labelled_close_up))
    if made is None:
        views.mkdir()
        route_views.make_views(inputs, views, 7, {"objects": list(takes)})
        made = VIEWS_MADE[takes, model.read_bytes(), labelled_close_up] = pathlib.Path(tempfile.mkdtemp()) / "views"
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


def listed(folder, answer, takes=(TAKE,), again=None, labelled_close_up=False):
    """The views and list rows made with the list's batch faked to answer `answer(views, take)` (a dict, or an
    exception the batch holds), every ask after the first `again(views, take)` when given: the rows' inputs and the
    batches asked."""
    inputs, views = cast_views(folder, takes, labelled_close_up)
    asked = []
    original = route_list.ask

    def answered(bodies):
        asked.append(bodies)
        now = again if again is not None and len(asked) > 1 else answer
        return {take: (now(views, take) if isinstance(now(views, take), Exception) else json.dumps(now(views, take)))
                for take in bodies}

    route_list.ask = answered
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
    """The parts row's make as the table sets it (recheck_picks.make_parts), with no pick."""
    from score.stages.surfaces import recheck_picks
    out, picks = folder / "parts", folder / "no picks"
    out.mkdir()
    picks.mkdir()
    (picks / recheck_picks.FILE).write_text(json.dumps({"takes": {}, "not_picked": {}}))
    recheck_picks.make_parts({**rows, recheck_picks.ROW: picks}, out, 7, {"objects": [TAKE]})
    return {**rows, "surfaces-parts": out}


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


def red_and_blue(views, take):
    """Each box's region labelled its own finish."""
    return two_finish_answer(views)


def blue_left_out(views, take):
    """The red box's region labelled, the blue box's left out."""
    return two_finish_answer(views, lambda view, colour: 1 if colour == RED else None)


def all_red(views, take):
    """Both boxes' regions labelled the red finish: the blue finish labels none."""
    return two_finish_answer(views, lambda view, colour: 1)


def all_blue(views, take):
    """Both boxes' regions labelled the blue finish: the red finish labels none."""
    return two_finish_answer(views, lambda view, colour: 2)


def blue_in_red(views, take):
    """The blue box listed in the red token, its labels its own."""
    return dict(two_finish_answer(views), finishes=[finish_entry("red paint"), finish_entry("blue paint",
                                                                                           token="sign-red")])


def blue_in_steel(views, take):
    """The blue box listed as bare steel (a wrong surface), its labels its own."""
    import part_judge
    with tempfile.TemporaryDirectory() as temporary:
        library = pathlib.Path(temporary)
        palette = route_parts.palette_library.read({"finish-route-palette": paletted(library),
                                                    "surface-library": libraried(library)})
        steel = part_judge.code(list(route_parts.palette_library.take_surfaces({"kind": "two_boxes"},
                                                                               palette)).index("bare_steel"))
    return dict(two_finish_answer(views), finishes=[finish_entry("red paint"),
                                                    finish_entry("blue paint", surface=steel, token="steel")])


def close_up_labelled(views, take):
    """Every region shown in every view, the laid close-up's among them, labelled by its colour: the red box's (in
    the texture's or the close-up's light) the red finish, the blue box's the blue, the GREEN label a third finish."""
    record = json.loads((views / "views.json").read_text())[take]
    finish_of_srgb = {RED: 1, LIT_RED: 1, BLUE: 2, LIT_BLUE: 2, GREEN: 3}
    shown = route_list.regions_shown(views / take, route_list.labelled_views(views / take, record["views"]))
    labels = [{"view": view, "region": region + 1, "finish": finish_of_srgb[tuple(record["regions"][region]["srgb"])]}
              for view, regions in shown.items() for region in regions]
    return {"finishes": [finish_entry("red paint"), finish_entry("blue paint", token="bay-three"),
                         finish_entry("green label")], "labels": labels}


def batch_expired(views, take):
    """The two boxes' take lost with its batch, the other answered."""
    if take == TAKE:
        return route_ask.google_batch.Unanswered("the batch ended JOB_STATE_EXPIRED")
    return two_finish_answer(views)


# The list, split and parts rows on the two boxes (route_list.make_list, route_split.make_split,
# recheck_picks.make_parts), the list's batch faked: (case, (the boxes' colours, the first answer, the answer every
# later ask gets or None for the same, the takes, a close-up laid), (the batches asked, the finishes the take's labels
# use or None for no list written, the follow-up ask's words or None), (the list's verdict, its finding or None),
# (the split's verdict, its finding or None, the faces each finish takes) or None for no split, (each finish's `by`,
# the surfaces finishes keep by index, the views' texture off every finish's colour, the close-up faults' count and
# words) or None for no parts.)
# Batch 1 try 4 (2026-10-25): 134 takes were gaps for a surface over dE 32 from a raw texture region, whose colours
# carry the picture's light: a finish is held against the close-up's colour, never the light-baked texture.
# #36, 2026-10-30: habitat's dining table listed its cloth runner and labelled no region with it, so the split gave
# it no face: such a take is asked once more, the answer kept where it labels the finish, the first where it still
# does not. Owner, 2026-10-28: unassigned area over route_split.UNASSIGNED_MOST is a gap. The paper: the views are
# split into colour regions only so the list can label them; the split decides by the labels alone.
# route_split.squared_votes on a sphere whose right view labels every face finish 0 and top view finish 1: (case,
# the axis its faces' normals lie along, the finish the squarer view gives).
SQUARED = [
    ("a side face takes the right view's finish", 0, 0),
    ("an upward face takes the top view's finish", 1, 1),
]

# route_split.split_fault on a take's shares: (case, shares, the fault's words or None for no gap).
SPLIT_SHARES = [
    ("unassigned at the quarters box's share: walked, no gap",
     {"unseen": 0.5, "disagree": 0.0, "unassigned": route_split.UNASSIGNED_MOST}, None),
    ("unassigned just over what a real take showed: a gap",
     {"unseen": 0.5, "disagree": 0.0, "unassigned": round(route_split.UNASSIGNED_MOST + 0.0001, 4)}, "unassigned"),
]

# route_split.voted_finishes on that sphere voted finish 1 everywhere but the faces named: (case, the faces, their
# votes, the finish they take).
SPLIT_VOTES = [
    ("a face seen in a region no label reaches takes its nearest label's finish", "face 7", [0.0, 0.0], 1),
    ("a patch tied between the two finishes takes the finish round it", "patch", [0.5, 0.5], 1),
    ("a patch not tied takes its own finish", "patch", [0.6, 0.5], 0),
]

# route_split.voted_finishes on a thin tube (annulus) whose outer wall's upper half views give finish 0, its lower half
# and both rims finish 1, its inner wall seen by none (a TRELLIS.2 shell's inner side, #173): (case, the wall, what is
# read, what it is). Walked along the surface, the inner wall took the rim's finish 1 and was a part of its own.
SPLIT_SHELL = [
    ("the inner wall takes the finish of the outer wall behind it, not the rim's", "inner upper", "finish", "finish 0"),
    ("and joins the outer wall's part, not a hidden part of its own", "inner upper", "part", "the outer wall's part"),
]

LISTED = [
    ("every finish labels its region, two takes in one batch", ((RED, BLUE), red_and_blue, None, (TAKE, OTHER), None),
     (1, {0, 1}, None, 2, None), ("pass", None), ("pass", None, [12, 12]), None),
    ("every finish labels its region, parted", ((RED, BLUE), red_and_blue, None, (TAKE,), None),
     (1, {0, 1}, None, 2, None), ("pass", None), ("pass", None, [12, 12]),
     ({"red paint", "blue paint"}, ["the list", "the list"], {}, set(), False, None, None)),
    ("the blue box listed in red: the split decides by the labels alone", ((RED, BLUE), blue_in_red, None, (TAKE,),
                                                                            None),
     (1, {0, 1}, None, 2, None), ("pass", None), ("pass", None, [12, 12]), None),
    ("the blue box's region left out: unassigned, a gap", ((RED, BLUE), blue_left_out, None, (TAKE,), None),
     (2, {0}, "finish 2 (blue paint) but labels no region", 2, None), ("pass", None), ("fail", "unassigned", None),
     None),
    ("the blue finish labels no region, asked once more and labelled", ((RED, BLUE), all_red, red_and_blue,
                                                                        (TAKE,), None),
     (2, {0, 1}, "finish 2 (blue paint) but labels no region", 2, None), ("pass", None), ("pass", None, [12, 12]),
     None),
    ("asked once more and the red now labels none: no fewer, the first stands", ((RED, BLUE), all_red, all_blue,
                                                                                (TAKE,), None),
     (2, {0}, "finish 2 (blue paint) but labels no region", 2, None), ("pass", None), None, None),
    ("a texture shaded off its tokens, the close-up near them", ((SHADED_RED, SHADED_BLUE), red_and_blue, None,
                                                                 (TAKE,), "split"),
     (1, {0, 1}, None, 2, None), ("pass", None), ("pass", None, [12, 12]),
     ({"red paint", "blue paint"}, ["the list", "the list"], {}, set(), True, 0, None)),
    ("the blue box as bare steel, off its colour", ((RED, BLUE), blue_in_steel, None, (TAKE,), "split"),
     (1, {0, 1}, None, 2, None), ("pass", None), ("pass", None, [12, 12]),
     ({"red paint", "blue paint"}, ["the list", "off its colour"], {1: "bare_steel"}, set(), False, 1,
      "bare_steel")),
    ("the two boxes' batch ended: a gap named by the list", ((RED, BLUE), batch_expired, None, (TAKE, OTHER), None),
     (1, None, None, 2, None),
     ("fail", f"{TAKE}: no finish list (no usable answer: Unanswered('the batch ended JOB_STATE_EXPIRED'))"), None,
     None),
    # greenhouse desk (2026-10-29): the close-up showed a red DANGER label, a blue decal and teal screens the raw
    # take's texture lacks, so no region of any view had them and no part owned them. The close-up, laid on the model
    # through its camera, is one more view of the regions: its GREEN label (on the red box's front, in no texture) has
    # a region, the list labels it (the laid close-up's regions the ask's last part), its faces take that finish and
    # it is a part; the finishes the views do show stay voted.
    ("a finish only the close-up shows gets its region, its faces and a part", ((RED, BLUE), close_up_labelled, None,
                                                                                (TAKE,), "views"),
     (1, {0, 1, 2}, None, 3, "the view named close-up"), ("pass", None), ("pass", None, [2, 10, 12]),
     ({"red paint", "blue paint", "green label"}, ["the list", "the list", "off its colour"], {},
      {"red paint"}, False, None, None)),
]


def bake_made(folder, rows):
    """The bake made through the rows, the cloud call faked: each take's job writes back its labelled take, its
    models' entries and a baked model into its own made folder. The bake's inputs, its output and the calls made
    (with the jobs' files)."""
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
            pathlib.Path(job["outputs"][1]).mkdir(parents=True, exist_ok=True)
            (pathlib.Path(job["outputs"][1]) / "two_boxes.gltf").write_text("{}")
        return subprocess.CompletedProcess(command, 0, "", "")
    original = route_bake.subprocess.run
    route_bake.subprocess.run = run
    try:
        route_bake.make_bake(inputs, out, 7, {})
    finally:
        route_bake.subprocess.run = original
    return inputs, out, calls


# The hub's right console (2026-11-05): its close-up grey, its bake 53% rust (a*b* 30.8 off; likeness's measure),
# 47% the grey; a console baked right: its grey within a few a*b*, its copper trim 12 off (the light's own shift on a right surface), its
# hazard label baked its token, airlock's small box's hazard_yellow, 27 a*b* off the label's close-up (the listed
# check's to judge, finish_parts.COLOUR_DELTA_E, not the bake's).
CONSOLE_GREY, CONSOLE_RUST, CONSOLE_COPPER = [46.1, 0.8, 2.4], [45.0, 18.0, 28.0], [43.0, 9.0, 10.0]
HAZARD_TOKEN, HAZARD_CLOSE_UP = [76.2, 1.1, 73.4], [73.3, -2.1, 46.4]


def console_bake(rusted):
    """A console's baked triangles as baked_colour.surface_offs reads them, rusted as the hub's or baked right."""
    grey = [[CONSOLE_GREY[0], CONSOLE_GREY[1] + (index % 5) - 2, CONSOLE_GREY[2] - (index % 3)] for index in range(100)]
    colour = np.array(grey[:47] + [CONSOLE_RUST] * 53 if rusted else
                      grey[:75] + [CONSOLE_COPPER] * 15 + [HAZARD_TOKEN] * 10)
    named = ["hull"] * 100 if rusted else ["hull"] * 75 + ["trim"] * 15 + ["label"] * 10
    return baked_colour.surface_offs(colour, np.ones(100), named,
                                     {"hull": CONSOLE_GREY, "trim": [42.9, 8.9, 14.9], "label": HAZARD_CLOSE_UP},
                                     {"hull": [CONSOLE_GREY], "trim": [CONSOLE_COPPER], "label": [HAZARD_TOKEN]})


# The paint's colour gate on the bake (baked_colour.judge_colour), each baked surface measured on the bake's own map
# against its close-up, its measure faked to the console's triangles: (case, rusted, each surface's share baked off,
# (the verdict, its "baked off", its findings), the batch gaps' checks or None for no gap file).
CONSOLES = [
    ("a console baked right: its grey, its copper trim 12 off, its hazard label its token", False,
     {"hull": 0.0, "trim": 0.0, "label": 0.0}, ("pass", 0, ()), None),
    ("the hub's right console baked 53% rust on a grey token: a batch gap of its take", True, {"hull": 0.53},
     ("fail", 1, (f"{TAKE}: two_boxes hull bakes 53% of its area over 20 a*b* off its close-up's {CONSOLE_GREY}",)),
     [baked_colour.GATE]),
]


def two_take_parts(rows, folder, rough):
    """A parts output at `folder` of TAKE as made and OTHER a copy of it with its first part's listed roughness at
    `rough`."""
    shutil.copytree(rows["surfaces-parts"], folder)
    shutil.copytree(folder / TAKE, folder / OTHER)
    method = json.loads((folder / "parts.json").read_text())
    other = json.loads(json.dumps(method["takes"][TAKE]))
    other["parts"][0]["settings"]["roughness"] = rough
    (folder / "parts.json").write_text(json.dumps(dict(method, takes={**method["takes"], OTHER: other})))
    return folder


def bake_jobs(rows, parts, out, kept, held, brought):
    """{take: its job's kept content (tools/cloud/kept.py)} of the bake made from `parts` into `out`, the cloud call
    faked to bring nothing back; each job's outputs appended to `brought`."""
    found = {}

    def run(command, **_):
        for path in (pathlib.Path(path) for path in command if str(path).endswith("-job.json")):
            job = json.loads(path.read_text())
            found[json.loads(pathlib.Path(job["args"][0]).read_text())[route_bake.place_line.TAKE]] = \
                kept.identity(job, "system")[1]
            brought.append([pathlib.Path(output) for output in job["outputs"]])
        return subprocess.CompletedProcess(command, 1, "", "faked")
    out.mkdir()
    held.setenv(kept.MAKING, str(out))
    held.setattr(route_bake.subprocess, "run", run)
    inputs = {"surfaces": rows["surfaces"], "surfaces-parts": parts, "finish-route-palette": rows["finish-route-palette"],
              "surface-library": rows["surface-library"], "resting rules": REPO / "data/checks/resting.json"}
    with pytest.raises(RuntimeError, match="paint and bake failed"):  # nothing came back: no take baked
        route_bake.make_bake(inputs, out, 7, {})
    return found


def recheck_made(rows, out, answer):
    """The recheck made on the parted `rows` into `out`, its one batch faked to answer `answer` (a dict, or an exception
    the batch holds): the take's record, its verdict and the batches asked."""
    asked = []
    original = route_recheck.ask
    route_recheck.ask = lambda bodies: asked.append(bodies) or {
        take: answer if isinstance(answer, Exception) else json.dumps(answer) for take in bodies}
    try:
        out.mkdir()
        route_recheck.make_recheck(rows, out, 7, {"objects": [TAKE]})
    finally:
        route_recheck.ask = original
    return json.loads((out / "recheck.json").read_text())[TAKE], route_recheck.judge_recheck(out, rows, {}), asked


def picks_made(rows, folder, answer):
    """The picks row made on the split `rows` into folder/picks as the table sets it (colour_picks.make_picks), its one
    ask faked to answer `answer`, then the parts made with its picks and without the picks row: the takes asked, the
    rows' inputs with the picks, and the parts' parts.json bytes with and without the picks."""
    from score.stages.surfaces import colour_picks
    original, asked = recheck_picks.ask, []
    recheck_picks.ask = lambda bodies: asked.extend(bodies) or {take: json.dumps(answer) for take in bodies}
    picks, made, plain = folder / "picks", folder / "parts", folder / "plain"
    for path in (picks, made, plain):
        path.mkdir(parents=True)
    try:
        colour_picks.make_picks(rows, picks, 7, {"objects": [TAKE]})
    finally:
        recheck_picks.ask = original
    picked = {**rows, recheck_picks.ROW: picks}
    recheck_picks.make_parts(picked, made, 7, {"objects": [TAKE]})
    parts_kept.make_parts(rows, plain, 7, {"objects": [TAKE]})
    return asked, picked, (made / "parts.json").read_bytes(), (plain / "parts.json").read_bytes()


def remade_parts(rows, takes, folder):
    """surfaces-parts made again on `rows` with the picks file holding `takes`: its parts.json and the picks folder."""
    picks, out = folder / "picks again", folder / "parts again"
    shutil.rmtree(picks, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    picks.mkdir()
    out.mkdir()
    (picks / recheck_picks.FILE).write_text(json.dumps({"takes": takes, "not_picked": {}}))
    recheck_picks.make_parts({**rows, recheck_picks.ROW: picks}, out, 7, {"objects": [TAKE]})
    return json.loads((out / "parts.json").read_text()), picks


def grey_over_blue(views):
    """The two boxes' list with "grey paint" (hull-trim) listed over the blue box: off its colour."""
    return {**two_finish_answer(views), "finishes": [finish_entry("red paint", wear="worn"),
                                                     finish_entry("grey paint", token="hull-trim")]}


# The recheck on the two boxes' parts (route_recheck.make_recheck), its one batch faked: (case, the parts' colour check
# (finish_parts.COLOUR_DELTA_E: held wide, or at 0.5 so a finish lies off its colour), the batch's answer, (the batches
# asked, the take passed, its suggestion, its fault's start or None for none, colour faults found), (the verdict, a
# word of its first finding or None)).
RECHECKS = [
    ("both finishes match: one ask, a pass", 1000.0,
     {"finishes": [{"finish": 1, "matches": True, "why": "red"}, {"finish": 2, "matches": True, "why": "blue"}]},
     (1, True, {}, None, False), ("pass", None)),
    ("the red too dull: a fail with its fitting suggestion", 1000.0,
     {"finishes": [{"finish": 1, "matches": False, "why": "too dull", "token": "alarm", "roughness": 0.2},
                   {"finish": 2, "matches": True, "why": "blue"}]},
     (1, False, {"red paint": {"token": "alarm", "roughness": 0.2}}, "red paint: too dull", False), ("fail", "too dull")),
    ("the batch gave no answer for the take: a gap", 1000.0,
     route_ask.google_batch.Unanswered("the batch gave no answer for it"),
     (1, False, {}, "no usable answer", False), ("fail", None)),
    ("a take the free colour check fails is never asked", 0.5, {"finishes": []},
     (0, False, {}, "the free colour check, not asked", True), ("fail", "the free colour check, not asked")),
]


# #118 point 3: the red finish the recheck fails, suggesting alarm (red_pipes' rust-brown for the list's copper).
FAILING_RED = {"finish": 1, "matches": False, "why": "painted, not copper", "token": "alarm", "roughness": 0.2,
               "metal": 0.1}


# The picks row (colour_picks.make_picks) and the parts made with it: a suggestion whose token lies within dE 32 of the
# finish's close-up colour is applied, so the parts, the bake and the recheck after it take it; none is applied when
# its token lies off the close-up's colour or the failing finish names no token, nor for a take the free colour check
# failed that keeps no token of its listed hue (group C), and the parts are then made as without the picks row:
# (case, the list's answer, FAILING_RED's changes or None for no ask, the pick's token or None, the not-picked words
# or None, each finish's `by` in the parts made with the picks).
PICKS = [
    ("the red's suggested alarm lies within dE 32 of its close-up: picked", two_finish_answer, {}, "alarm", None,
     ["the list", "the list"]),
    ("bay-three lies off the red's close-up colour: not picked", two_finish_answer, {"token": "bay-three"}, None,
     "lies dE", ["the list", "the list"]),
    ("a failing finish naming no token: not picked", two_finish_answer, {"metal": None}, None, "no library token",
     ["the list", "the list"]),
    ("grey paint listed over the blue box is off its colour: never asked, not picked", grey_over_blue, None, None,
     "no library token of its listed hue", ["the list", "off its colour"]),
]


# surfaces-parts made again on the picked row's rows with its red pick changed: a pick lies on the finish its words
# name, never by its number alone; one naming no finish of this list (a remake pairing the picks with another list,
# 2026-11-12: "brown plastic" on flat's "brown plastic cord and switch") or a token the scene library lacks (galley's
# brushed-steel) is dropped by name and the parts still make, as without the pick; the picks gate refuses a pick off
# its close-up's colour; a split whose faces carry a finish its list lacks (docking_airlock's IndexError) is refused
# by name before anything is made: (case, the pick's number, its changes or None for no pick on the list cut to its
# first finish, (the red finish's token, the dropped pick's words or None, the picks gate's verdict, the refusal's
# words or None)).
REMADE = [
    ("a pick numbered 2 naming 'Red  Paint!' lies on the list's red paint", "2", {"finish": "Red  Paint!"},
     ("alarm", None, "pass", None)),
    ("a pick naming no finish of the list is dropped by name", "1", {"finish": "blue paint coat and trim"},
     (None, "no finish of the list is it", "pass", None)),
    ("a pick on a token the scene library lacks is dropped by name", "1", {"token": "brushed-steel"},
     (None, "brushed-steel is no token of the scene library", "fail", None)),
    ("a pick lying off its close-up's colour fails the picks gate", "1", {"measured_lab": [90.0, -40.0, 60.0]},
     ("alarm", None, "fail", None)),
    ("a split made on another list is refused by name", "1", None, (None, None, None, "made on another list")),
]


# recheck_picks.finish_for on flat's list: (case, the pick's finish words, its number, the finishes already taken, the
# finish it lies on or None).
FINISH_LIST = [{"finish": "rusty painted steel"}, {"finish": "brown plastic cord and switch"},
               {"finish": "weathered galvanised sheet steel"}, {"finish": "brushed stainless steel"}]
FINISH_FOR = [
    ("its words with one more colour word", "Rusty grey painted steel", 3, set(), 0),
    ("its words hyphenated, with a noun more", "Weathered galvanised sheet-steel housing", 0, set(), 2),
    ("words that are part of a finish's", "brown plastic", 1, set(), None),
    ("words of no finish, the number a finish's", "bare brushed steel sheet and tube", 3, set(), None),
    ("its finish taken already: one pick a finish", "rusty painted steel", 0, {0}, None),
]


# colour_picks.colour_fitting (#118 group C): a take the free colour check failed, which the recheck never asks, is
# picked on the scene library's token nearest its off finish's close-up colour within dE 32 among those keeping what
# the list meant (finish_parts.hue_kept); a dim close-up pulled foliage to a ground grey, 2026-11-12: (case, a finish
# fitting its colour listed first, the off finish's words (listed in plain steel, seen bay-three), (its key, the
# token picked) or None, the why's words or None).
COLOUR_FITTING = [
    ("blue steel seen blue takes bay-three, its recipe, roughness and metal its list's", True, "blue steel",
     ("2", "bay-three"), None),
    ("grey steel seen blue keeps no grey token near it", False, "grey steel", None,
     "no library token of its listed hue"),
    ("a finish with no colour words never moves off its listed hue", False, "steel", None,
     "no library token of its listed hue"),
]


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


STEEL_ONLY = coined(("steel", "#9ba2a9"))
FRESH = {"palette": coined(*((token, TOKENS[token]) for token in ("steel", "glass", "sign-red", "regolith"))),
         "wear": "new", "cause": "fresh", "dirt": 0.0, "dirt_token": "regolith"}
# The palette row, each case made once by its one ask: (case, the answer, where it is asked, its verdict, a word of
# its first finding, words its question holds, words it never holds, the pictures sent before the question,
# palette.json's fields (None: none written), fields it leaves out). A scene is asked over its own locked concept
# and leaves out what only its people wear; a line no scene owns over every concept, its takes' close-ups after
# them (astronaut-made, 2026-10-23: asked over the concepts alone the people's palette had no brown, and the brown
# trousers its close-up shows took moon-dust, 20 L* lighter).
PALETTE_ASKS = [
    ("its own tokens in its order, a token named twice keeping its first colour, no old token offered",
     {"palette": coined(("steel", "#9BA2A9"), ("hazard", "#f2c21a"), ("glass", "#24313a"), ("regolith", "#8b8883"),
                        ("steel", "#000000")),
      "wear": "worn", "cause": "scuffed decks", "dirt": 1.7, "dirt_token": "regolith"},
     {}, "pass", None, ("locked concept", "people in it wear", "grime itself", "The picture is the scene's locked "
                        "concept."), ("sign-red", "hull-trim", "close-up"), 1,
     {"tokens": {"steel": "#9ba2a9", "hazard": "#f2c21a", "glass": "#24313a", "regolith": "#8b8883"},
      "wear": {"level": "worn", "dirt": 1.0, "dirt_token": "regolith", "cause": "scuffed decks"}}, ("close_ups",)),
    ("a wear off the method's levels", {"palette": STEEL_ONLY, "wear": "shiny", "cause": "", "dirt": 0.2,
                                        "dirt_token": "steel"}, {}, "fail", "no usable answer", (), (), 1, None, ()),
    ("unanswered", route_ask.google_batch.Unanswered("none for it"), {}, "fail", "none for it", (), (), 1, None, ()),
    ("too narrow", {"palette": STEEL_ONLY, "wear": "new", "cause": "", "dirt": 0.0, "dirt_token": "steel"}, {},
     "fail", "a palette of 1 tokens", (), (), 1, {"tokens": {"steel": "#9ba2a9"}}, ()),  # written, judged too narrow
    ("a colour not #rrggbb", {"palette": coined(("steel", "grey")), "wear": "new", "cause": "", "dirt": 0.0,
                              "dirt_token": "steel"}, {}, "fail", "no usable answer", (), (), 1, None, ()),
    ("a line no scene owns, over every concept, covering its people", FRESH, {"place": "people", "concept": False},
     "pass", None, ("every scene", "skin and hair"), ("people in it wear",), 2, {"pictures": 2}, ()),
    ("its takes' close-ups after the concepts", FRESH,
     {"place": "people", "concept": False, "close_ups": ("worker-t1", "pilot-t1")}, "pass", None,
     ("The last 2 pictures are close-ups", "first 2 pictures"), (), 4, {"close_ups": 2}, ()),
]


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


SQUARE = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]
ROOM = {"w": 6.0, "d": 4.0, "outline": SQUARE,
        "walls": [{"from": one, "to": two, "thick": 0.2, "tall": 2.5}
                  for one, two in zip(SQUARE, SQUARE[1:] + SQUARE[:1])],
        "roofs": [{"kind": "flat", "points": SQUARE, "eave": 2.5, "top": 2.5}],
        "stairs": [{"kind": "stair", "points": [[4.0, 2.0], [5.0, 2.0], [5.0, 4.0], [4.0, 4.0]]}]}
PANEL = {"name": "panel", "family": "paint", "recipe": "painted_metal", "token": "hull-trim", "roughness": 0.4,
         "metal": 0.0, "colours": {"bare": "steel"}, "sound": "steel_plate", "kinds": ["two_boxes"]}
GLAZED = [{"name": "photo_print_glazed", "family": "glass", "recipe": "glass", "token": "hull-trim", "roughness": 0.1,
           "metal": 0.0, "sound": "glass", "kinds": ["framed_photo"]},
          {"name": "window_glass", "family": "glass", "recipe": "glass", "token": "hull-trim", "roughness": 0.05,
           "metal": 0.0, "sound": "glass", "kinds": ["window_pane"]}]
PHOTO_KINDS = {"kinds": ("framed_photo", "window_pane")}
GROUND_ROWS = [{"id": "crater_1", "noun": "crater", "name": "large crater", "terrain": True},
               {"id": "drift", "noun": "drift", "name": "sand drift", "terrain": True},
               {"id": "hut", "noun": "hut", "name": "hut"}]
# The surface-library row, each case made once by its one ask over the scene palette and its takes' kinds: (case,
# the answer, what it is made on, its verdict, its findings exactly (None: unheld), findings it holds, its findings
# naming a picture (None: unheld), words its question holds, words it never holds, {schema field: (offered, never
# offered)}). Every kind a take, a ground row of the kept inventory or the shell a locked plan lays is covered by a
# surface; a ground row with the recipe its words name, else its body's physics (the Moon's: airless, regolith). No
# recipe that paints a picture is offered or kept (surface-library@people, 2026-10-22: suit_patches as `printed`,
# with no picture, stopped the bake), and a kind that shows a picture needs a surface that draws one (flat's framed
# photo as one grey glass sheet, checkout 62).
LIBRARY_ASKS = [
    ("made fresh from its palette and kinds", {"surfaces": [
        {"name": "Hull Panel", "family": "Paint", "recipe": "painted_metal", "token": "hull-trim", "roughness": 0.4,
         "metal": 0.0, "colours": {"bare": "steel", "second": "glass"}, "sound": "steel_plate", "kinds": ["two_boxes"]},
        {"name": "window", "family": "glass", "recipe": "glass", "token": "glass", "roughness": 1.6, "metal": 0.0,
         "sound": "glass", "kinds": []}]}, {}, "pass", (), (), None,
     ("two_boxes: two boxes", "painted_metal", "colours: bare", "steel_grating",
      "- bare: the bare stuff under its paint"),
     (), {"recipe": (("glass",), ())}),
    ("a kind with no surface, a token and a sound off the library", {"surfaces": [
        {"name": "panel", "family": "paint", "recipe": "painted_metal", "token": "hull-trim", "roughness": 0.4,
         "metal": 0.0, "kinds": ["two_boxes"]}]}, {"kinds": ("two_boxes", "crate")}, "fail", None,
     ("kind crate has no surface", "panel: token None (bare) is not the palette's",
      "panel: sound surface None is not known"), None, (), (), {}),
    ("unanswered", route_ask.google_batch.Unanswered("none for it"), {}, "fail", None, (), None, (), (), {}),
    ("a locked plan's shell left bare", {"surfaces": [PANEL]}, {"plan": ROOM}, "fail", None,
     ("kind floor has no surface", "kind wall has no surface", "kind roof has no surface"), None,
     ("- wall: the room's walls",), (), {"kinds": (("floor", "wall", "roof", "stairs"), ())}),
    ("a locked plan's shell covered",
     {"surfaces": [dict(PANEL, kinds=["two_boxes", "floor", "wall", "roof", "stairs"])]},
     {"plan": ROOM}, "pass", (), (), None, (), (), {}),
    ("a recipe that paints a picture", {"surfaces": [
        {"name": "patches", "family": "fabric", "recipe": "printed", "token": "hull-trim", "roughness": 0.4,
         "metal": 0.0, "kinds": ["two_boxes"]}]}, {}, "fail", None,
     ("patches: recipe printed paints a picture, and the library has none",), None,
     ("- pile: ", "- written: ", "(pile; written"), (), {"recipe": (("pile", "written"), scene_library.PICTURED)}),
    ("a picture shown by a plain glass sheet", {"surfaces": GLAZED}, PHOTO_KINDS, "fail", None, (),
     ["kind framed_photo shows a picture and no surface of it draws one (written)"],
     (f"- framed_photo: framed photo{scene_library.PICTURE_WORDS}", "- window_pane: window pane\n", "never its\nglass"),
     (), {}),
    ("a picture drawn by its surface", {"surfaces": [{**GLAZED[0], "recipe": "written", "colours": {"second":
                                                                                                    "hull-trim"}},
                                                     GLAZED[1]]}, PHOTO_KINDS, None, None, (), [],
     (f"- framed_photo: framed photo{scene_library.PICTURE_WORDS}", "- window_pane: window pane\n", "never its\nglass"),
     (), {}),
    ("ground rows by their natural ground", {"surfaces": [
        {"name": "moon_dust", "family": "regolith", "recipe": "regolith", "token": "hull-trim", "roughness": 0.9,
         "metal": 0.0, "colours": {"second": "steel"}, "sound": "stone", "kinds": ["two_boxes", "crater"]},
        {"name": "drift_paint", "family": "paint", "recipe": "cast_metal", "token": "steel", "roughness": 0.5,
         "metal": 0.0, "sound": "stone", "kinds": ["drift"]}]}, {"grounds": GROUND_ROWS}, "fail",
     ("ground drift has no surface of its recipe sand",), (), None,
     ("- crater: regolith (Moon:", "- drift: sand (the row drift says sand)", "crater: large crater"), ("hut",), {}),
]
# A scene library's shell surfaces: the shell laid from the locked plan and a prop's paint take one answer
# (palette_library.SHELL_KINDS), each shell part the first variant the library gives one of its kinds: (part, its
# surface). No wall surface and no crate is a shell surface; a stair with no stairs kind takes the floor's.
SHELL_KINDS = {"floor": ["deck_plate", "rubber_mat"], "ceiling": ["ceiling_panel"], "wall": [], "crate": ["crate_wood"]}
SHELL_PARTS = [("stair", "deck_plate"), ("roof", "ceiling_panel"), ("wall", None)]


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


def a_closeup(path, mask):
    """A Pixal3D input: `mask` as its alpha over grey, at `path`."""
    alpha = np.where(mask, 255, 0).astype(np.uint8)
    Image.fromarray(np.dstack([np.full(mask.shape + (3,), 128, np.uint8), alpha])).save(path)
    return path


IDENTITY = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
BED = {"id": "bed", "name": "bunk bed", "thing": "prop:bed_take"}
LAMP = {"id": "ceiling_lamp", "name": "ceiling lamp", "anchor": "on:ceiling_beam", "thing": "prop:lamp_take"}


# #36 (2026-10-29: 154 of env1's 406 baked models stood tumbled, camp's bunk bed rolled 44 degrees; the bake turned
# garage's ceiling lamp 50 degrees; 2026-10-30: quarters' string lights, leaned by its close-up's look-down, were
# turned 34 degrees off it, outline 0.544 to 0.101; lab's desk_divider, a Pixal3D take, outlined its close-up 0.467 as
# made and 0.296 turned). route_bake.stood_square on one labelled box take a row: (case, its hand-in row, model, take,
# the take's roll in degrees and its (x, y, z) size, the model's row size, built in code, its close-up (None, or the
# pose it is drawn from: "made" or "turned" square), what it stands as). "square": its box within a degree of its frame
# and back on these proportions, turned at least this many degrees (or None); "kept"/"kept from": its made pose kept,
# `stood` saying exactly this or starting with it, and the bake check leaving it out for the same reason; "same": left
# as it was; "outline kept"/"outline turned": kept as made with both outlines named, or turned as with no close-up.
STAND_SQUARE = [
    ("a 2 x 1 x 0.6 m take rolled 40 degrees is stood square", BED, "bed_1", "bed_take", 40, (2.0, 1.0, 0.6),
     [2.0, 1.0, 0.6], False, None, ("square", (2.0, 1.0, 0.6), 30.0)),
    ("a row whose design lays it lying keeps the turn it was made in",
     {"id": "rear", "name": "crashed rocket rear section", "thing": "prop:rear_take"}, "rear_1", "rear_take", 40,
     (2.0, 1.0, 0.6), [2.0, 1.0, 0.6], False, None, ("kept from", "its design lays it lying (crashed)")),
    ("one standing square already is left as it is", {"id": "bed", "thing": "prop:bed_take"}, "bed_1", "bed_take", 0,
     (2.0, 1.0, 0.6), [2.0, 1.0, 0.6], False, None, ("same",)),
    ("a code build keeps the pose its code made", {"id": "string_lights", "thing": "prop:lights_take"}, "lights_1",
     "lights_take", 40, (2.0, 1.0, 0.6), [2.0, 1.0, 0.6], True, None, ("kept", tumble.CODE_BUILD)),
    ("an L desk drawn flatter than its take has its tilt taken off on the up it stands on, never laid on its back",
     {"id": "desk", "thing": "prop:desk_take"}, "desk_1", "desk_take", 30, (0.7, 0.42, 0.6), [1.5, 1.0, 0.8], False,
     None, ("square", (0.7, 0.42, 0.6), None)),
    ("a ceiling lamp anchored on a beam hangs: its pose kept", LAMP, "ceiling_lamp_1", "lamp_take", 40,
     (2.0, 1.0, 0.6), [2.0, 1.0, 0.6], False, None, ("kept from", "it hangs")),
    ("a Pixal3D take whose made pose outlines its close-up better keeps it", BED, "bed_1", "bed_take", 40,
     (2.0, 1.0, 0.6), [2.0, 1.0, 0.6], False, "made", ("outline kept",)),
    ("a Pixal3D take whose turned pose outlines its close-up at least as well is turned", BED, "bed_1", "bed_take", 40,
     (2.0, 1.0, 0.6), [2.0, 1.0, 0.6], False, "turned", ("outline turned",)),
]

# The one guard list (tumble.keeps_pose), read by row kind, anchor and words, never by a name: (case, row, the place's
# rows, why it keeps its pose: None, any reason (True), ("is", exactly) or ("from", its start)). A person (the people
# route), a hanging row (the resting rules' hanging words, or its anchor the ceiling, by word or by its holder's
# ceiling group), a cable and ground debris (no up), a lying one; a stool on the floor is not kept. #36 (2026-10-29):
# hangar's limp floor cables were turned 31 degrees, cockpit's seated pilot widened to his box with its chair.
KEEPS_POSE = [
    ("a person", {"id": "pilot", "route": "people", "anchor": "on:pilot_seat"}, [], ("is", tumble.PERSON)),
    ("a lamp anchored on a ceiling beam", {"id": "ceiling_lamp", "name": "ceiling lamp", "anchor": "on:ceiling_beam"},
     [], ("from", "it hangs (anchored on:ceiling_beam)")),
    ("a light on its holder's ceiling group", {"id": "light_1", "name": "light", "anchor": "on:ceiling_panels"},
     [{"id": "ceiling_panels", "group": "kit: ceiling"}], True),
    ("a glove hanging by its words", {"id": "glove", "name": "hanging glove", "anchor": "on:cabinet"}, [], True),
    ("floor cables have no up", {"id": "floor_cables", "name": "thick red cables", "anchor": "floor"}, [],
     ("is", "no up (cables): it rests as it was made")),
    ("ground debris has no up", {"id": "rocks", "name": "rubble pile"}, [], True),
    ("a crashed rocket section lies", {"id": "rear", "name": "crashed rocket rear section"}, [], True),
    ("a stool on the floor is not kept", {"id": "stool", "name": "stool", "anchor": "floor", "route": "prop"}, [], None),
]

# route_bake.squared_again, the check's own measure on each copy as it bakes (#36, 2026-10-29: habitat's stove stood
# 7.1 degrees on its labelled take and was not turned, then 12.6 baked and failed `stands square`; hangar's pipe
# valves were turned from 32.8 to 12.4 degrees on their unsteady box and kept that turn): (case, the entries (copied),
# each copy's points by name, the measuring round, the copies to bake again, each model's base after: "made" (as
# made), "turned" (the turn it had), "square" (a turn that stands its copy within a degree), its `kept` or None).
STOVE_BOX = trimesh.creation.box(extents=(0.8, 0.9, 0.6)).vertices
VALVES = {"pipe_valves_1": {"base": [round(value, 6) for value in np.array(rolled(20)).reshape(-1)],
                            "size": [0.8, 0.9, 0.6], "stood": {"made": IDENTITY}}}
# an unsteady box, as the valves': a round blob's oriented box stands over 10 degrees off, its frame box as tight
UNSTEADY = trimesh.creation.icosphere(subdivisions=3).vertices * np.array([0.5, 0.42, 0.3]) @ np.array(rolled(12.35)).T
SQUARE_AGAIN = [
    ("a copy 12.6 degrees off, never turned, is turned and baked again; a square one is done",
     {"stove_1": {"base": IDENTITY, "size": [0.8, 0.9, 0.6]}, "oven_1": {"base": IDENTITY, "size": [0.8, 0.9, 0.6]}},
     {"stove_1": STOVE_BOX @ np.array(rolled(12.6)).T, "oven_1": STOVE_BOX}, 1, ["stove_1"],
     {"stove_1": ("square", None), "oven_1": ("made", None)}),
    ("one the bake turned still off after the last measuring takes back the turn it was made in", VALVES,
     {"pipe_valves_1": UNSTEADY}, "last", [], {"pipe_valves_1": ("made", "its turn left it {degrees} degrees off its "
                                                                         "frame as baked: kept as made")}),
    ("one the bake turned that is square as baked keeps its turn", VALVES, {"pipe_valves_1": STOVE_BOX}, "last", [],
     {"pipe_valves_1": ("turned", None)}),
]

# take_outline (scored on the card, where likeness.py cannot load: tools/usd/compare.py pulls in pxr) against the
# likeness gate's likeness_row.whole_best_way over pixal_cut's cut, on the bed's take and its STAND_SQUARE close-ups:
# (case, the close-up's pose, the row's size).
OUTLINE_SIZES = [("a row seen at its look-down", "made", [1.0, 0.6, 0.4]),
                 ("one lying flat seen from above", "made", [2.0, 2.0, 0.1]),
                 ("one lying flat seen from above, its close-up turned", "turned", [2.0, 2.0, 0.1])]
# STAND_SQUARE's outcomes whose made pose is kept, so `stands square` leaves them out
KEPT_POSES = ("kept", "kept from", "outline kept")


# A moving door's recess (route_bake.recessed, each recess a relation names cut into its holder's entry when the job is
# written, by route_bake.recess_box): a recess within its face's span less a side wall (RECESS_BACK) at each end, from
# 5 cm out of the face to its depth, never past RECESS_BACK of the model's far side (a back), each holder entry left as
# it was and a holder no relation names cut nowhere. #72: a 6 m wide, 0.5 m thick door hinged on its left (-x) swings a
# quarter turn into its 12 m module through its S face (z 6), at 90 degrees lying x -3.5 to -3 and z 0 to 6: its
# recess, widened on that side by its thickness plus 5 cm and its swing's 6.05 m deep, holds it 5 cm clear of the side
# and the back. #36 (2026-10-29): base's garage door at its module's W end lay flush against the kept side wall at full
# open, the recess having taken the 5 cm its room had for clearance: its room is its 0.5 m thickness, the clearance and
# the wall (score/review/holders RECESS_MARGIN, RECESS_WALL), the assembly keeps door and room within the face (its
# hinge edge at -6 plus the room fitting.beside keeps below it), so at full open the door clears the wall by 5 cm and,
# closed, its latch side by as much. #72 (base's garage door, its middle 7.695 m left of the module's, room 0): kept
# flush with the span's end (base's recess cut its module's W side wall away, 2026-10-29), a static door's relation
# beside it cuts nothing; a sliding door's recess is its thickness deep, with its width of room along the face:
# (case, the relations, the holder, its cut wanted, the room the assembly keeps below the door or None, the door's
# edges as each lies against the cut: (axis, the cut's bound, the edge, its least clearance, its most or None)).
DOOR_HOLDERS = {"module_1": {"size": [12.0, 12.0, 12.0], "cuts": []}, "shed_1": {"size": [4.0, 3.0, 4.0], "cuts": []}}
GARAGE_SWING = {"model": "module_1", "axis": "z", "side": 1.0, "along": -7.695, "wide": 6.0, "room": 0.0, "tall": 8.0,
                "base": 0.0, "depth": 6.05}
END_ROOM = 0.5 + holders.RECESS_MARGIN + holders.RECESS_WALL  # as holders.recess_of gives a swing (its own test)
END_HINGE = -6.0 + END_ROOM  # where the assembly lays the door's hinge edge (fitting.on_holder)
DOORS = [
    ("a 6 m door hinged left at full open lies 5 cm clear of its recess's side and back",
     [{"recess": dict(GARAGE_SWING, along=0.0, room=0.55, room_side=-1.0)}], "module_1",
     [[-3.55, 0.0, -0.05], [3.0, 8.0, 6.05]], None,
     [(0, "low", -3.5, 0.05, None), (2, "low", 0.0, 0.05, None), (0, "high", -3.0, 0.0, None),
      (2, "high", 6.0, 0.0, None)]),
    ("a door at its face's end clears the kept side wall at full open by its margin, and its latch side",
     [{"recess": dict(GARAGE_SWING, room=END_ROOM, room_side=-1.0, room_way=[-1.0, 0.0])}], "module_1",
     [[-5.95, 0.0, -0.05], [0.65, 8.0, 6.05]], END_ROOM,
     [(0, "low", END_HINGE - 0.5, holders.RECESS_MARGIN, holders.RECESS_MARGIN),
      (0, "high", END_HINGE + 6.0, holders.RECESS_MARGIN, None)]),
    ("base's garage door is cut flush with its span's end, a static door beside it cuts nothing",
     [{"item": "GARAGE DOOR 1", "row": "garage_door", "recess": GARAGE_SWING}, {"item": "SHUTTER 1", "row": "shutter"}],
     "module_1", [[-5.95, 0.0, -0.05], [0.05, 8.0, 6.05]], None, []),
    ("a sliding door's recess is its thickness deep, its width of room along the face",
     [{"recess": dict(GARAGE_SWING, model="shed_1", axis="x", side=-1.0, along=0.0, wide=1.0, room=1.0, tall=2.0,
                      depth=0.15)}], "shed_1", [[-2.05, 0.0, -0.5], [-1.85, 2.0, 1.5]], None, []),
]


# The people line's bake takes its specs and wear from the repository's library by place; every old material was
# retired (2026-10-21), so the entry rows give it a stand-in library's (no surface: the entries are the subject).
WEAR = (0.4, 0.3)


def a_folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix="bake-job-", dir=PROPS_HOME / "store-tests"))


def a_json_file(folder, name, record):
    path = folder / f"{name}.json"
    path.write_text(json.dumps(record))
    return path


def a_box_take(folder, take, extents):
    """A labelled take of one part: a box of `extents` (x, y, z) written as a .ply, as labels.py writes parts."""
    labelled = folder / "labelled" / take
    labelled.mkdir(parents=True)
    trimesh.creation.box(extents=extents).export(labelled / "hull_white.ply")
    return labelled


def a_handin(row, take):
    """A place's hand-in of one row, its object the take `take` made on the prop route."""
    return {"rows": [row], "objects": {row["id"]: {"route": "prop", "take": take}}}


def an_entry_case(case, place, model, take, extents, design, want, *, inventory=None, code=False, person=False,
                  turn=None, rules=False):
    """One bake entry row: a model's take (a box of `extents`, None for no take, stood by the finish's `turn`) and
    the entry its place's surface data writes (`design`, None for none), its hand-in, its code build mark, its
    `kind` person and its pose rules; `want` the entry's fields laid, or `refused` the bake's refusal."""
    return {"case": case, "place": place, "model": model, "take": take, "extents": extents, "design": design,
            "want": want, "inventory": inventory, "code": code, "person": person, "turn": turn, "rules": rules}


WRITTEN_OUT = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [0.5, 0.9, 1.1], "faces": 19000, "foot": 0.0}
TUNNEL = {"id": "tunnel", "name": "right connecting tunnel", "anchor": "ground", "size": [3.0, 1.5, 1.5],
          "box": [959, 369, 2578, 1038]}
CEILING_LAMP = {"id": "ceiling_lamp", "name": "ceiling lamp", "anchor": "on:ceiling_beam", "box": [927, 603, 994, 725]}
PILOT = {"id": "pilot", "route": "people", "anchor": "on:pilot_seat", "box": [812, 687, 946, 906],
         "kit": [0.5, 1.8, 0.3]}
OFFICER = dict(PILOT, id="officer", box=[0, 0, 10, 100])
STOOL = {"id": "stool", "name": "stool", "anchor": "floor", "route": "prop", "box": [812, 687, 946, 906],
         "kit": [0.5, 1.8, 0.3]}
STOOD = np.array(rolled(8)) @ np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])  # a quarter, leaned


def a_design(size, faces=19000):
    return {"size": size, "faces": faces, "foot": 0.0}


# The bake's entries (place_line.bake_entries): an entry the data writes out is taken as written, a model with
# none stops the bake by name. A design's take has no hand-set turn: of 0 and 90 degrees, the one whose labelled
# footprint fits its row's wide and deep. A slender row (a sagging string 8 by 0.01 by 0.01, its take hanging 1 m) and
# a code build (its take's code.json route "code") are laid as one scale, their longest side the row's, never fitted
# side by side to the box (airlock's locker lamp built 0.046 m across, outline 0.813 built, 0.409 baked so,
# 2026-10-29); a code build standing for a row that lies (hangar's wall pipes, built 22 m up its receding picture for
# a 32 m run) is laid along its row, never standing 32 m in a 15 m hangar. A Pixal3D take is laid at its own
# proportions scaled as one to the largest that fits within its row (#10, 2026-11-08: old_station's tunnel was
# stretched side by side, outline 0.70 made, 0.466 stretched), a hanging row so too. A person (#36: cockpit's seated
# pilot was widened to his SAM 3 box, 1.205 m, and his A-pose officer squeezed into 0.5 m) keeps his take's own width
# for his row's height whatever his box; a stool of the same take and row is laid within its row. A take whose surface
# data names it a person (`kind`, as people_rows.py writes each look's, its hand-in no objects) is turned back by the
# finish's own turn into his raw take's pose (#36, 2026-10-31: likeness@people failed 3 of its 9 looks, pilot 0.465,
# each A-pose body turned a quarter round and leaned), keeps his own width there, and is never stood square.
BAKE_ENTRIES = [
    an_entry_case("the data's own entry is taken as written", "hangar", "pedestal_1", "pedestal-t1", None,
                  WRITTEN_OUT, {**WRITTEN_OUT, "regions": []}),
    an_entry_case("a model the data writes no entry for stops the bake", "hangar", "lost_1", "lost-t1", None, None,
                  {"refused": "no entry for lost_1", "refusal": "the data writes none"}),
    an_entry_case("a take long along z for a row wide along x is turned a quarter round", "hub", "bench_1", "bench-t1",
                  (0.5, 0.9, 2.0), a_design([2.0, 0.9, 0.5]), {"base": bake_job.TURNS[90], "yaw": 90.0}),
    an_entry_case("a take already along its row is not turned", "hub", "bench_2", "bench-along-t1", (0.5, 0.9, 2.0),
                  a_design([0.5, 0.9, 2.0]), {"base": bake_job.TURNS[0]}),
    an_entry_case("a slender row keeps its take's proportions", "street", "string_1", "string-t1", (0.05, 1.0, 8.0),
                  a_design([8.0, 0.01, 0.01]), {"base": bake_job.TURNS[90], "size": [8.0, 1.0, 0.05]}),
    an_entry_case("a Pixal3D take is laid within its row's box", "airlock", "lamp_1", "lamp-t1", (0.4, 0.15, 0.046),
                  a_design([0.4, 0.1, 0.1], 5000), {"size": [0.32, 0.1, 0.037]}),
    an_entry_case("a code build bakes at its own section", "airlock", "lamp_2", "lamp-built-t1", (0.4, 0.15, 0.046),
                  a_design([0.4, 0.1, 0.1], 5000), {"base": bake_job.TURNS[0], "size": [0.4, 0.15, 0.046]},
                  code=True),
    an_entry_case("a code build for a row that lies is laid along it", "hangar", "pipes_1", "pipes-t1",
                  (4.9, 22.0, 0.4), a_design([0.4, 0.4, 32.0]), {"size": [7.127, 0.582, 32.0]}, code=True),
    an_entry_case("a code build for a row that stands keeps standing", "hangar", "pipes_2", "pipes-up-t1",
                  (4.9, 22.0, 0.4), a_design([0.4, 32.0, 0.4]), {"size": [7.127, 32.0, 0.582]}, code=True),
    an_entry_case("a Pixal3D tunnel is laid the largest within its row", "old_station", "tunnel_1", "tunnel-t1",
                  (3.0, 0.856, 1.589), a_design([3.0, 1.5, 1.5]), {"size": [3.0, 0.97, 1.5]},
                  inventory=a_handin(TUNNEL, "tunnel-t1")),
    an_entry_case("a hanging row is laid within it too", "old_station", "ceiling_lamp_1", "ceiling_lamp-t1",
                  (0.498, 0.868, 0.502), a_design([0.4, 0.5, 0.4]), {"size": [0.344, 0.5, 0.347]},
                  inventory=a_handin(CEILING_LAMP, "ceiling_lamp-t1")),
    an_entry_case("a person keeps his take's width for his row's height", "cockpit", "pilot_1", "pilot-t1",
                  (0.6, 1.0, 0.3), a_design(PILOT["kit"], 5000), {"size": [1.08, 1.8, 0.3]},
                  inventory=a_handin(PILOT, "pilot-t1"), rules=True),
    an_entry_case("a person is never squeezed to his row whatever his box", "cockpit", "officer_1", "officer-t1",
                  (0.58, 1.0, 0.3), a_design(OFFICER["kit"], 5000), {"size": [1.044, 1.8, 0.3]},
                  inventory=a_handin(OFFICER, "officer-t1"), rules=True),
    an_entry_case("a thing of the same take and row is laid within its row", "cockpit", "stool_1", "stool-t1",
                  (0.6, 1.0, 0.3), a_design(STOOL["kit"], 5000), {"size": [0.5, 1.0, 0.3]},
                  inventory=a_handin(STOOL, "stool-t1"), rules=True),
    an_entry_case("a people line look stands in his raw take's pose", "people", "pilot-made", "pilot-made-s1",
                  (0.6, 1.0, 0.3), a_design([0.5, 1.8, 0.3], 5000),
                  {"size": [1.08, 1.8, 0.3], "raw pose": STOOD.T, "kept": "person"},
                  inventory={"place": "people", "rows": [{"id": "pilot-made", "prop": "pilot-made",
                                                          "box": [0, 0, 40, 100]}]},
                  person=True, turn=STOOD, rules=True),
]
ENTRY_CHECKS = {"refused", "refusal", "yaw", "raw pose", "kept"}  # a row's wants beyond the entry's own fields


# The bake job's stood takes (bake_job.refitted): a take stood square by the bake (its `stood`, no `kept`) is laid
# again within its row at its new turn's proportions, one the stand kept, a code build's and a person's as they were.
REFITS = [  # (case, its turn, refitted's own words, the size laid or None: as it was)
    ("stood square: laid again within its row", 90, {}, [0.6, 0.6, 1.0]),
    ("kept by the stand", 0, {}, [1.0, 0.6, 0.6]),
    ("a code build's", 90, {"built": True}, None),
    ("a person's", 90, {"person": True}, None),
]


# A flat row (the model gate's "flat") is laid by its face, its depth held apart (flat_fit.py, #10 2026-11-12):
# quarters' picture frame, its take 0.43 deep for its height, was laid 0.039 by 0.046 by 0.02 m for its 0.15 by 0.2
# by 0.02 m row, 6% of its face. Its face now fills the row, its depth held at 6 cm (3 times its row's).
FACE_FITS = [  # (case, the made size, the row, laid)
    ("a door 10 cm deep for its 5 cm row keeps its 10 cm", (1.0, 2.0, 0.1), [1.0, 2.0, 0.05], [1.0, 2.0, 0.1]),
    ("a lumpy window 1.1 m deep for its 2 cm row is 6 cm", (1.2, 1.0, 1.1), [1.2, 1.0, 0.02], [1.2, 1.0, 0.06]),
    ("the face within its row on both sides, stretched 20% at most toward it", (0.5, 0.5, 2.0), [2.0, 1.0, 0.1],
     [1.2, 1.0, 0.3]),
]


# --- body_faces ---

METHOD = pathlib.Path(__file__).resolve().parents[3] / "data/library/materials.json"


ANSWER = {"palette": [{"token": "regolith-grey", "colour": "#8a8580"}, {"token": "crater-dark", "colour": "#3b3a38"}],
          "face": {"family": "Regolith", "recipe": "regolith", "token": "regolith-grey", "roughness": 0.95,
                   "metal": 0.0, "colours": {"second": "crater-dark"}}}


GROUND = ["regolith", "Moon: airless, its dust ground by impacts"]


FACES = [  # (case, body, style, ground, the ask's reply, the make's error or None, the face made's fields or None)
    ("made from one ask in the method's recipes", {"body": "moon", "name": "Moon", "radius_km": 1737.4},
     "worn NASA-punk", GROUND, json.dumps(ANSWER), None,
     {"surface": "moon_face", "family": "regolith", "hex": "#8a8580", "recipe": "regolith", "recipe_by": GROUND[1]}),
    ("no answer is named", {"body": "mars", "name": "Mars"}, "", GROUND, ValueError("no json"), None, None),
    ("its physics the setting lacks", {"body": "vesta", "name": "Vesta"}, "",
     [None, "Vesta: no surface pressure in the setting"], json.dumps(ANSWER),
     "no natural ground for its face: Vesta: no surface pressure", None),
]


LEVELS = ["new", "worked", "worn"]
OFF_PALETTE = {"palette": coined(("steel", "#9ba2a9"), ("hazard", "#f2c21a"), ("glass", "#24313a"),
                                 ("lamp", "#ffffff")),
               "wear": "worn", "cause": "scuffed", "dirt": 0.4, "dirt_token": "soot-grime"}  # env1's shiplock, 10-27
ON_PALETTE = {**OFF_PALETTE, "palette": [*OFF_PALETTE["palette"], *coined(("soot-grime", "#3a3633"))]}
REPAIRS = [  # (case, the row's module, Claude's first answer, the asks made)
    ("a palette answer off its own palette is asked once more, told why", scene_palette, OFF_PALETTE, 2),
    ("a good palette answer is asked once", scene_palette, ON_PALETTE, 1),
    ("another row's answer is never asked again", scene_library, OFF_PALETTE, 1),
]


# The paint reads a finish's turn off the final model (place_line.recovered_turn) whatever code stood it, and lays a
# raw take by it (place_line.finished_frame): a take stood by a turn no option of today's glb_file gives (30 degrees
# round up; the airlock's four, stood before glb_file.squared changed, 48939c57) has that turn read back exactly off
# its final model's vertices; a final that is not its finished file's vertices turned gets none, and the replay
# decides; a raw image-to-3d take left facing +Z (its stamp), whose finish turn is recovered off its final model, is
# turned back half round before that turn, as the finish turned it before slimming: laid on its final, not tipped
# over (galley's sink and workshop's desk lay on their backs, 2026-10-30): (case, the take, its final moved off its
# finished file by (z metres), the turn read back or None, laid on its final's bounds by finished_frame).
CRATE_TURN = np.array([[math.cos(math.radians(30)), 0.0, math.sin(math.radians(30))], [0.0, 1.0, 0.0],
                       [-math.sin(math.radians(30)), 0.0, math.cos(math.radians(30))]])
STOOL_TILT = trimesh.transformations.rotation_matrix(math.radians(30), [1, 0, 0])[:3, :3]
PAINT_TURNS = [
    ("a take stood by a turn no option of glb_file gives has it read back exactly", "crate_1", 0.0, CRATE_TURN, False),
    ("a final moved off its finished file's vertices turned gets no turn", "crate_1", 0.05, None, False),
    ("a raw take still facing +Z is laid on its final by its recovered turn", "stool_1", 0.0, STOOL_TILT.T, True),
]
