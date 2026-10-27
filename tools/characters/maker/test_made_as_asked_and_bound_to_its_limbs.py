"""A body is made only as asked, and bound to its own limbs (the character maker): a spec is refused before anything
is rented unless it is approved, names a picture or words, an absolute picture and words for every outfit, and an
experimental route runs only when asked for, however it is started; a make runs its steps on a rented machine in
their order with its own files (the identity off the take's close-up, the route on the built body, the clips and
the rig with no clip from here), a failed tucks record predicts the same failure only on the same inputs; the prop
route asks each part with three seeds, lets most usable answers decide and gives an unanswered part its mirror's
answers; its rig fits the mean skeleton into the mesh at the mean bones' lengths, its weights come back on their own
limbs, a tuck runs under its garment and a hard part rides one joint; the poke checks read a tuck under cloth as
hidden, a hard part's stretch and cloth through cloth; and the people route keeps each region's points on their own
limb, cuts the webs and closes them, keeps the made face until the owner decides, tucks the head under its collar
and draws the body under a cut web only where cloth hides it.

Nothing here loads a model or rents a machine: made-up meshes (tubes, grids, boxes), small spec and record files,
and the machine handed a make faked at prop_person.on_characters. Two cases need the props environment
(~/.farm-factory-props/env) and skip without it. The owner rule `route_head.FACE == "made"` (#26: until he decides)
is checked as his rule.

Breaks that turn each test red (each applied once and seen red, 2026-10-26; file names under tools/characters/maker
unless named):
- test_the_checked_in_specs_can_be_made: spec.person_problems' `if not spec.get("face"):` made `"head"`.
- test_a_spec_without_approval_is_refused: problems_of's REQUIRED check made `problems = []`.
- test_a_spec_needs_a_picture_or_words: problems_of's picture-or-description check made `if False:`.
- test_a_relative_picture_is_refused_and_one_from_home_is_kept: `.expanduser()` dropped from the path check.
- test_an_outfit_without_words_is_refused: person_problems' `if outfit not in spec.get("outfit_words", {})` made
  `if False`.
- test_reading_raises_with_every_problem: spec.read's `if problems:` made `if False:`.
- test_experimental_routes_run_only_when_asked_for_and_the_shipped_chain_never: make.refusals'
  `if route in EXPERIMENTAL_ROUTES and not experimental:` made `if False:`.
- test_the_experimental_routes_refuse_when_started_round_make: prop_person.main's `if not options.experimental:` made
  `if False:`.
- test_an_outfit_without_a_palette_can_name_shoes_as_boots: prop_parts.BOOTS without "black leather shoe".
- test_a_far_surface_with_no_faces_is_left_out_not_crashed_on: prop_build.far_body's `if not mine.any(): continue`
  dropped.
- test_any_outfit_with_words_can_be_split_and_one_without_is_refused_on_the_pc: prop_parts.problems_of returns `[]`.
- test_a_failed_tucks_record_predicts_a_gap_only_on_the_same_inputs: tucks_record's `not all(... > 0 ...)` made
  `not any(...)`; and, apart, tucks_inputs without the people tools' code; and, apart, tucks_inputs' test filter
  without `or path.name.startswith("test_")` (a test edit then moves the hash).
- test_the_cloth_count_reads_the_routed_bodys_own_node_whatever_its_outfit: counts_by_clips' outfit node taken as the
  first skinned node, the far body's `!= "far"` dropped.
- test_the_identity_is_read_off_the_takes_close_up: identity's steps `("identity",)` made `("identity", "route")`.
- test_a_kimodo_clip_is_made_with_the_fixed_seed_and_records_it: people/clips.py kimodo_arguments' `"--seed",
  str(CLIP_SEED)` made `"--seed", "0"`.
- test_the_route_is_the_bodys_binding_after_the_build: prop_person.route's steps `("identity", "route")` made
  `("route",)`.
- test_the_route_step_rebuilds_the_built_body_on_the_base_under_it: prop_chain.route's skel_usd.py run dropped.
- test_the_clips_and_the_rig_are_one_make_that_takes_no_clip_from_here: clips_rig's steps made `("rig", "clips")`.
- test_each_part_is_asked_with_every_seed: prop_parts.seeded's `for seed in SEEDS` made `SEEDS[:1]`.
- test_most_usable_answers_decide: judged_by_most's `max(picks, ...)` made `min(picks, ...)`.
- test_an_unanswered_part_takes_its_mirror_images_answers: mirrored's `mirror_of[following] = int(mirror)` made
  `int(part)`.
- test_each_outfit_has_its_palette: palette_of returns FALLBACK_PALETTE always.
- test_skeleton_into_itself_comes_back: prop_rig.placed's bone `length` made `* 1.1` longer.
- test_weights_into_itself_come_back: prop_rig.matched's `good = (squared <= distance ** 2)` made
  `(squared < 0)` (nothing matched).
- test_lowered_arms_turn_the_arm_bones: placed's `along_axis(places[parent], fit[chain], length)` made `mean[chain]`.
- test_inpainting_blends_the_unmatched_strip: inpainted's solved weights made zero (`0 * splu(...)`).
- test_tuck_runs_under_the_garment: tucks.tucked_ring's `places + away * directions * TUCK_LENGTH` made `-`.
- test_pokes_read_inside_and_outside: pokes.tuck_out's `np.where(inside, -distance, distance)` swapped.
- test_pokes_read_a_band_under_two_overlapping_parts_as_hidden: tuck_out's winding-number second ask dropped (the
  2026-10-10 fault: a band under both overlapping parts read as outside).
- test_pokes_hold_cloth_to_the_shipped_bodys_record: against's `>` made `<`.
- test_a_leaning_body_is_stood_level: prop_rig.stood's `range(LEVEL_ROUNDS)` made `range(0)`.
- test_thinning_keeps_the_parts_shut: thinned_part's `preserve_border=True` made `False`.
- test_a_band_takes_its_own_limbs_weights: tucks.limb_weights' pool made every garment point.
- test_a_hard_part_rides_one_joint_and_the_cloth_by_it_follows: prop_build.rigid_joint's boot `side + "Foot"` made
  `side + "Shin"`.
- test_pokes_read_a_hard_parts_stretch: pokes.stretch's `max(worst, ...)` made `min(worst, ...)`.
- test_piping_is_cut_down_the_outside_of_a_limb: piping.across_outer_line's outer half `> 0` made `< 0`.
- test_a_flat_sheet_crosses_nothing: pokes.crossing_pairs' shared-corner filter and `usable &` both dropped (either
  one alone stays green: a flat sheet's edges all share a corner or lie in its plane).
- test_a_sheet_through_another_is_counted: edge_crossings' search radius `halves[rows] + 2.0 ** size` made
  `halves[rows] * 0`.
- test_a_lone_point_takes_its_neighbours_region: route_bind.majority's `labels = votes.argmax(1)` made `labels`.
- test_an_edge_whose_binds_jump_is_web_and_a_touching_seam_is_not: web_edges' jump threshold made `jump > 0`.
- test_the_underarm_and_the_crotch_are_cut_but_the_shoulder_top_is_not: underarm_edges' `height - UNDERARM_BELOW` made
  `height + 1`.
- test_a_cut_is_closed_on_each_side_by_its_own_fan: closed's `kept = faces[~cut]` made `faces[cut]`.
- test_a_limb_point_keeps_only_its_chain_and_its_shoulder: kept_to_limb's zeroing of the other joints dropped.
- test_the_face_is_one_setting_and_keeps_the_made_face_by_default: route_build.kept_surfaces' drawn face's
  `("skin_head",)` made `()`.
- test_the_collar_line_is_filled_round_the_neck: route_head.collar_line's empty-bin fill dropped.
- test_points_under_the_collar_are_listed_last: tuck_order's order made `np.arange(len(points))`.
- test_the_neck_is_appended_under_the_old_head: Extension's `new = piece_faces[~same[piece_faces].all(1)]` made
  `piece_faces`.
- test_the_lowest_band_of_the_drawing_is_painted_skin: painted_neck's `low = points[:, 1] < ...` made `>`.
- test_the_scalp_is_drawn_under_the_hair: under_hair's `first[moving] - HAIR_GAP` made `+`.
- test_the_main_shapes_keep_offsets_made_of_few_directions: principal_shapes' largest-first `[::-1]` dropped.
- test_the_longest_edge_of_each_triangle: route_stretch.longest_edges' `.max(1)` made `.min(1)`.
- test_a_boots_shaft_follows_the_shin_and_its_sole_the_foot: route_build.shafted's `FOOT_DEGREES - degrees` made
  `degrees - FOOT_DEGREES` (the sole on the shin, the shaft on the foot), or shaft_tops' `> ... + SHAFT_FROM` made
  `<` (a tall boot left wholly on its foot).
- test_a_web_bridging_the_legs_fails_the_stretch_check: route_stretch.grown's `- rest` made `/ rest` (a ratio, not
  metres), or MOST_METRES raised past the 0.21 m the pre-route astronaut's crotch web grew walking.
- test_the_body_under_a_cut_web_is_drawn_inside_in_the_cut_garments_cloth: under_layer's `np.isfinite(near) &`
  dropped (the base drawn beyond UNDER_REACH).
- test_cloth_next_to_a_skin_part_rides_its_weights_and_takes_no_correctives: skin_share's own-family `mine` made every
  point.
- test_the_body_under_a_cut_web_is_not_drawn_where_it_would_show_through_the_cloth: under_layer's
  `& (under_cloth(inset, garments) >= UNDER_INSET)` dropped (the 2026-10-22 white patches).
- test_the_route_reads_the_body_node_its_outfit_named: body_node's `!= "far"` dropped.
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
import pytest
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent / "people")]
import piping  # noqa: E402
import pokes  # noqa: E402
import prop_build  # noqa: E402
import prop_parts  # noqa: E402
import prop_rig  # noqa: E402
import route_bind  # noqa: E402
import route_build  # noqa: E402
import route_head  # noqa: E402
import route_stretch  # noqa: E402
import spec  # noqa: E402
import tucks  # noqa: E402


# --- a make is asked for, and runs its steps on a rented machine in their order ------------------------------------

PERSON = {"name": "someone", "kind": "person", "approved": "the owner", "description": "a person",
          "hair": "short hair", "face": "a face", "route": "prop", "outfit_words": {"work": "a work suit"}}


def test_the_checked_in_specs_can_be_made():
    """Every spec written from a design (data/people/specs, score/stages/people_rows.py) passes the maker's checks and
    carries its person's name (its takes go to that person's candidates folder) in a file named <name>.json."""
    for path in sorted((REPO / "data/people/specs").glob("*.json")):
        found = spec.read(path)
        assert found["name"] == path.stem


def test_a_spec_without_approval_is_refused():
    assert "no approved" in spec.problems_of(dict(PERSON, approved=""))


def test_a_spec_needs_a_picture_or_words():
    problems = spec.problems_of(dict(PERSON, description=None))
    assert "neither a picture nor a description" in problems


def test_a_relative_picture_is_refused_and_one_from_home_is_kept():
    assert any("not an absolute path" in problem for problem in spec.problems_of(dict(PERSON, picture="a.png")))
    assert not spec.problems_of(dict(PERSON, picture="~/a.png"))


def test_an_outfit_without_words_is_refused():
    assert "no outfit_words for gown" in spec.problems_of(dict(PERSON, outfits=["gown"]))
    assert "route 'drape' is not prop" in spec.problems_of(dict(PERSON, route="drape"))


def test_reading_raises_with_every_problem(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "bad", "kind": "robot"}))
    with pytest.raises(spec.SpecError, match="no approved.*kind 'robot'"):
        spec.read(path)


def test_experimental_routes_run_only_when_asked_for_and_the_shipped_chain_never():
    """Fault (audit of 2026-10-11, items 1-3): make.py over the old character specs started paid prop-route runs
    (the player fails tucks and pokes, Nev is not made) and the animal route had never run on a world; the shipped
    person chain and its garment drapes were retired on 2026-10-21, so a person on no route is refused always."""
    import make

    prop = dict(PERSON, name="player_prop")
    animal = {"name": "fish", "kind": "animal", "approved": "the owner", "description": "a fish"}
    shipped = {key: value for key, value in dict(PERSON, name="nev").items() if key != "route"}
    refused = make.refusals([prop, animal, shipped], experimental=False)
    assert [line.split(":")[0] for line in refused] == ["player_prop", "fish", "nev"], refused
    assert [line.split(":")[0] for line in make.refusals([prop, animal, shipped], experimental=True)] == ["nev"]
    assert "retired" in make.refusals([shipped], experimental=True)[0]


def test_the_experimental_routes_refuse_when_started_round_make(tmp_path):
    """Fault (review of 2026-10-11): --experimental was checked only in make.py, so prop_person.py run by hand and
    route.make called directly made a prop-route person or an animal without it."""
    written = tmp_path / "player.json"
    written.write_text(json.dumps(dict(PERSON, name="player", route="prop", outfit_words={"work": "a work suit"})))
    started = subprocess.run([sys.executable, str(REPO / "tools/characters/maker/prop_person.py"),
                              str(written), "--who", "a check", "--dry-run"],
                             capture_output=True, text=True)
    assert started.returncode != 0 and "only with --experimental" in started.stderr
    sys.path.insert(0, str(REPO / "tools/characters/animals"))
    import route
    with pytest.raises(SystemExit, match="only with make.py --experimental"):
        route.make({"name": "fish_tang"}, tmp_path, "a check", dry_run=True)
    assert not (tmp_path / "work").exists()


def test_an_outfit_without_a_palette_can_name_shoes_as_boots():
    """2026-10-13: with no shoe to choose, the judge gave kit_m_broad's shoes the belt's material."""
    props_python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not props_python.exists():
        pytest.skip("no props environment on this box")
    ask = ("import prop_parts; shoes = [name for name in prop_parts.palette_of('uniform-olive') "
           "if name in prop_parts.BOOTS]; print(shoes)")
    found = subprocess.run([str(props_python), "-B", "-c", ask], capture_output=True, text=True,
                           cwd=pathlib.Path(__file__).resolve().parent)
    assert found.returncode == 0 and "black leather shoe" in found.stdout


def test_a_far_surface_with_no_faces_is_left_out_not_crashed_on(tmp_path):
    """2026-10-13: kit_m_broad's wide take has no boot part, and the build crashed on the far body's empty boots."""
    far = tmp_path / "far.npz"
    np.savez(far, points=np.eye(3), faces=np.array([[0, 1, 2]]), surface_of_face=np.array([1]),
             weights=np.ones((3, 27)) / 27, surfaces=np.array(["skin", "clothes", "boots"]),
             colours=np.zeros((3, 3)))
    assert [item[0] for item in prop_build.far_body(far)] == ["clothes"]


def test_any_outfit_with_words_can_be_split_and_one_without_is_refused_on_the_pc(tmp_path):
    """2026-10-13: the parts step refused a kit's uniform-olive after 4 machine-minutes; now an outfit with words takes
    the work suit's material names for its roles, and one with no words is refused by `check` before any machine."""
    props_python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not props_python.exists():
        pytest.skip("no props environment on this box")
    script = pathlib.Path(__file__).resolve().parent / "prop_parts.py"
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"outfit_words": {"uniform-olive": "an olive uniform"}}))
    ask = [str(props_python), "-B", str(script), "check", str(tmp_path), "take", str(spec_file), "--outfit"]
    assert subprocess.run(ask + ["uniform-olive"], capture_output=True).returncode == 0
    refused = subprocess.run(ask + ["driver-suit"], capture_output=True, text=True)
    assert refused.returncode != 0 and "no outfit_words" in refused.stderr


def test_a_failed_tucks_record_predicts_a_gap_only_on_the_same_inputs(tmp_path, monkeypatch):
    """#21: the settled pokes.json with a tuck over the gate in every clip writes a record on the hash of the take,
    spec, parts and the maker's and people tools' code, which predicts the same failure (nothing bought); a clip
    that passed writes none, and any changed input, the people tools' code included, predicts nothing."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path)
    folder = prop_person.folder_of(PERSON, "work")
    (folder / "parts" / "pp-a_s1").mkdir(parents=True)
    (folder / "checks").mkdir()
    (folder / "take.txt").write_text("pp-a_s1")
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"first parts")
    clips = {"walk": {"worst_tuck_out_mm": 9.32, "frames_tuck_over": 40},
             "idle": {"worst_tuck_out_mm": 6.1, "frames_tuck_over": 0}}
    (folder / "checks" / "pokes.json").write_text(json.dumps({"clips": clips}))
    assert prop_person.tucks_record(PERSON, "work") is None and prop_person.predicted_tucks(PERSON, "work") is None
    clips["idle"]["frames_tuck_over"] = 3
    (folder / "checks" / "pokes.json").write_text(json.dumps({"clips": clips}))
    record = prop_person.tucks_record(PERSON, "work")
    assert record["worst_tuck_out_mm"] == 9.32 and record["clips"] == 2, record
    assert prop_person.predicted_tucks(PERSON, "work") == record
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"new parts")
    assert prop_person.predicted_tucks(PERSON, "work") is None
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"first parts")
    people = tmp_path / "tools" / "people"
    people.mkdir(parents=True)
    (people / "joins.py").write_text("# joins")
    (people / "test_joins.py").write_text("# a test")
    monkeypatch.setattr(prop_person, "HERE", tmp_path / "tools" / "maker")
    (tmp_path / "tools" / "maker").mkdir()
    prop_person.tucks_record(PERSON, "work")
    assert prop_person.predicted_tucks(PERSON, "work") is not None
    (people / "test_joins.py").write_text("# a test, edited")
    assert prop_person.predicted_tucks(PERSON, "work") is not None, "a test edit moved the hash"
    (people / "joins.py").write_text("# joins, fixed")
    assert prop_person.predicted_tucks(PERSON, "work") is None, "a people tools fix left the old prediction"


def test_the_cloth_count_reads_the_routed_bodys_own_node_whatever_its_outfit(tmp_path):
    """The route names a body's node work while its look's outfit is made (2026-10-22): the body-through-cloth count
    is asked for that node, not the outfit's name, so it is not refused on a node the routed body lacks."""
    import struct
    import prop_person
    document = {"nodes": [{"name": "far", "mesh": 0, "skin": 0}, {"name": "work", "mesh": 1, "skin": 0},
                          {"name": "Hips"}], "animations": [{"name": "walking"}]}
    text = json.dumps(document).encode().ljust(-(-len(json.dumps(document)) // 4) * 4, b" ")
    body = tmp_path / "body.glb"
    body.write_bytes(b"glTF" + struct.pack("<II", 2, 28 + len(text)) + struct.pack("<I", len(text)) + b"JSON" + text
                     + struct.pack("<I", 0) + b"BIN\x00")
    commands = prop_person.counts_by_clips(body, tmp_path)
    assert all(command[command.index("--outfit") + 1] == "work" for command in commands.values()), commands


def test_the_identity_is_read_off_the_takes_close_up(tmp_path, monkeypatch):
    """#26: SAM 3D Body reads the body under the clothes off the kept take's close-up (the A-pose picture is lost):
    one characters make whose only step is `identity`, its one file that close-up."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path / "candidates")
    monkeypatch.setattr(prop_person, "PIXAL", tmp_path / "pixal")
    asked = []
    monkeypatch.setattr(prop_person, "on_characters", lambda place, who, held, dry_run: asked.append(place))
    folder = prop_person.folder_of(PERSON, "work")
    folder.mkdir(parents=True)
    (folder / "take.txt").write_text("pp-a_s1")
    closeup = tmp_path / "pixal" / "pp-a_s1.svviews" / "input.png"
    closeup.parent.mkdir(parents=True)
    closeup.write_bytes(b"the close-up")
    assert prop_person.identity(PERSON, "work", "a test", None, True) is None
    machine = json.loads((asked[0] / "in" / "spec.json").read_text())
    assert machine["steps"] == ["identity"] and machine["program"] == "prop_chain.py", machine
    assert (asked[0] / machine["files"]["closeup"]).read_bytes() == b"the close-up"
    import prop_chain
    assert "identity" in prop_chain.STEPS


def test_a_kimodo_clip_is_made_with_the_fixed_seed_and_records_it(tmp_path):
    """#26: every clip is asked for with the one fixed seed, and its record beside it names the seed, so a lost clip
    is made again the same."""
    ask = ("import json, sys; import clips; arguments = clips.kimodo_arguments('walking', sys.argv[1]); "
           "clips.write_record('walking', sys.argv[1]); "
           "print(json.dumps([arguments, clips.CLIP_SEED, clips.SENTENCES['walking'][0], clips.MODEL]))")
    # its own process, in the people tools' folder: clips.py is found there by name
    done = subprocess.run([sys.executable, "-c", ask, str(tmp_path / "walking")], capture_output=True, text=True,
                          cwd=REPO / "tools/characters/people", check=True)
    arguments, seed, sentence, model = json.loads(done.stdout.splitlines()[-1])
    assert arguments[arguments.index("--seed") + 1] == str(seed), arguments
    record = json.loads((tmp_path / "walking.record.json").read_text())
    assert record == {"clip": "walking", "sentence": sentence, "seconds": 5.0, "model": model, "seed": seed}, record


def test_the_route_is_the_bodys_binding_after_the_build(tmp_path, monkeypatch):
    """#26: a full body is put through the people route on the same held machine as its build: one make reading the
    close-up (SAM 3D Body's identity), the fitted rig, the shell's fit and the built body; the garment settle is gone."""
    import prop_chain
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path / "candidates")
    monkeypatch.setattr(prop_person, "PIXAL", tmp_path / "pixal")
    asked = []
    monkeypatch.setattr(prop_person, "on_characters", lambda place, who, held, dry_run: asked.append((place, held)))
    folder = prop_person.folder_of(PERSON, "work")
    for name, words in (("take.txt", "pp-a_s1"), ("fit/rig.npz", "rig"), ("fit/shell.json", "{}"),
                        (f"out/{PERSON['name']}.glb", "built")):
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(words)
    closeup = tmp_path / "pixal" / "pp-a_s1.svviews" / "input.png"
    closeup.parent.mkdir(parents=True)
    closeup.write_bytes(b"the close-up")
    assert prop_person.route(PERSON, "work", "a test", "held", True) is None
    place, held = asked[0]
    machine = json.loads((place / "in" / "spec.json").read_text())
    assert machine["steps"] == ["identity", "route"] and held == "held", machine
    assert {name: (place / path).read_bytes() for name, path in machine["files"].items()} == {
        "closeup": b"the close-up", "fit": b"rig", "shell": b"{}", "body": b"built"}
    assert "settle" not in prop_chain.STEPS and "settle" not in prop_person.STAGE_WORK
    assert {"clips", "rig", "route", "identity"} <= set(prop_chain.STEPS)


def test_the_route_step_rebuilds_the_built_body_on_the_base_under_it(tmp_path):
    """prop_chain's route step: the base from the fitted rig, the shell's fit and the identity, the correctives of
    every clip of the built body, the route's build with them, its UsdSkel asset and its joins record, in that order,
    all on this make's own built body."""
    import prop_chain

    class Chain:
        out, spec, ran = tmp_path / "out", {"person": "a", "files": {"fit": "in/files/fit.npz",
                                                                      "shell": "in/files/shell.json"}}, []

        def file(self, relative):
            return tmp_path / relative

        def run(self, command):
            self.ran.append([str(part) for part in command])
            if pathlib.Path(command[1]).name == "route_build.py":
                pathlib.Path(command[5]).with_suffix(".json").write_text(json.dumps({"head": {"face": "made"}}))

    chain = Chain()
    chain.out.mkdir()
    (chain.out / "a.glb").write_text("built")
    assert prop_chain.route(chain) == "made"
    scripts = [pathlib.Path(command[1]).name + (f" {command[2]}" if command[1].endswith("route_base.py") else "")
               for command in chain.ran]
    assert scripts == ["route_base.py base", "route_base.py correctives", "route_build.py", "skel_usd.py", "joins.py"]
    base, build = chain.ran[0], chain.ran[2]
    assert base[3:6] == [str(tmp_path / "in/files/fit.npz"), str(tmp_path / "in/files/shell.json"),
                         str(chain.out / "identity.npz")]
    assert build[2] == str(chain.out / "a.glb") and build[5] == str(chain.out / "route" / "a.glb")
    assert "--correctives" in build and "--face" not in build, "the face is route_head.FACE, route_build's default"


def test_the_clips_and_the_rig_are_one_make_that_takes_no_clip_from_here(tmp_path, monkeypatch):
    """#26: people-clips-made's make: Kimodo's clips then the rig, on a rented machine; the lost work folder's
    clips are never copied up."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path / "candidates")
    asked = []
    monkeypatch.setattr(prop_person, "on_characters", lambda place, who, held, dry_run: asked.append((place, held)))
    assert prop_person.clips_rig(("standing", "bench"), tmp_path / "out", "a test", True) is None
    place, held = asked[0]
    machine = json.loads((place / "in" / "spec.json").read_text())
    assert machine["steps"] == ["clips", "rig"] and machine["clips"] == ["standing", "bench"] and held is None
    assert machine["approved"] and not (place / "in" / "motions").exists()


# --- the prop route's parts: three seeds, most usable answers, a mirror for the rest --------------------------------

MATERIALS = ["skin", "hair", "navy fabric"]


def answer(folder, part, seed, text):
    (folder / f"take-part{part:02d}-s{seed}.txt").write_text(text)


def test_each_part_is_asked_with_every_seed():
    with tempfile.TemporaryDirectory() as place:
        listing = pathlib.Path(place) / "questions.json"
        listing.write_text(json.dumps([{"name": "take-part00", "text": "?", "images": []},
                                       {"name": "other-part00", "text": "?", "images": []}]))
        asked = prop_parts.seeded(listing, ["take-part00"])
        jobs = json.loads(listing.read_text())
        assert asked == [f"take-part00-s{seed}" for seed in prop_parts.SEEDS]
        assert sorted(job["seed"] for job in jobs if job["name"].startswith("take")) == list(prop_parts.SEEDS)
        assert any(job["name"] == "other-part00" for job in jobs)


def test_most_usable_answers_decide():
    with tempfile.TemporaryDirectory() as place:
        folder = pathlib.Path(place)
        answer(folder, 0, 7, 'thinking... {"part": "pocket", "material": "M3"}')
        answer(folder, 0, 8, '{"part": "buckle", "material": "M1"}')
        answer(folder, 0, 9, '{"part": "pocket", "material": "M3"}')
        answer(folder, 1, 7, "thinking that never ends")
        answer(folder, 1, 8, '{"part": "hand", "material": "M1"}')
        found = prop_parts.judged_by_most(folder, "take", 3, MATERIALS)
        assert found == {0: "navy fabric", 1: "skin"}


def test_an_unanswered_part_takes_its_mirror_images_answers():
    # Faces left and right of x 0: on the right a hand (part 0, answered) and a cuff above it (part 1, answered); on
    # the left one part (2) the judge gave no answer for.
    middles = np.array([[-0.5, 1.0, 0.0], [-0.5, 1.2, 0.0], [0.5, 1.0, 0.0], [0.5, 1.2, 0.0]])
    part_of = np.array([0, 1, 2, 2])
    split, mirror_of = prop_parts.mirrored(part_of, [2], {0: "skin", 1: "navy fabric"}, middles)
    assert split[0] == 0 and split[1] == 1 and split[2] != split[3]
    assert mirror_of[split[2]] == 0 and mirror_of[split[3]] == 1


def test_each_outfit_has_its_palette():
    work, space = prop_parts.person_materials({}, "work"), prop_parts.person_materials({}, "space")
    assert "navy fabric" in work and "white suit fabric" in space and "skin" in work and "hair" in space
    assert all(prop_parts.ROLES[entry["family"]] for entry in space.values())


# --- the prop route's rig, tucks, pokes, piping and build on a body of tubes ---------------------------------------

JOINTS = {"Root": (0, 0.0, 0), "Hips": (0, 0.95, 0), "Spine1": (0, 1.1, 0), "Chest": (0, 1.3, 0),
          "Neck1": (0, 1.48, 0), "Head": (0, 1.58, 0)}
PARENTS = {"Hips": "Root", "Spine1": "Hips", "Chest": "Spine1", "Neck1": "Chest", "Head": "Neck1"}
for SIDE, SIGN in (("Left", 1.0), ("Right", -1.0)):
    JOINTS.update({SIDE + "Shoulder": (SIGN * 0.08, 1.42, 0), SIDE + "Arm": (SIGN * 0.2, 1.4, 0),
                   SIDE + "ForeArm": (SIGN * 0.375, 1.225, 0), SIDE + "Hand": (SIGN * 0.55, 1.05, 0),
                   SIDE + "Leg": (SIGN * 0.1, 0.9, 0), SIDE + "Shin": (SIGN * 0.1, 0.48, 0),
                   SIDE + "Foot": (SIGN * 0.1, 0.08, 0), SIDE + "ToeBase": (SIGN * 0.1, 0.02, 0.1)})
    PARENTS.update({SIDE + "Shoulder": "Chest", SIDE + "Arm": SIDE + "Shoulder", SIDE + "ForeArm": SIDE + "Arm",
                    SIDE + "Hand": SIDE + "ForeArm", SIDE + "Leg": "Hips", SIDE + "Shin": SIDE + "Leg",
                    SIDE + "Foot": SIDE + "Shin", SIDE + "ToeBase": SIDE + "Foot"})
NAMES = list(JOINTS)


def tube(start, end, radius, sections=24):
    """A closed cylinder from `start` to `end`."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    return trimesh.creation.cylinder(radius=radius, segment=[start, end], sections=sections)


def body(arm_reach=1.0, hand_at=(0.55, 1.05)):
    """The tube body, its arms reaching from the shoulders towards `hand_at` (x, height), `arm_reach` times as far."""
    parts = [tube((0, 0.85, 0), (0, 1.45, 0), 0.15), trimesh.creation.icosphere(3, 0.1).apply_translation((0, 1.6, 0)),
             tube((0, 1.42, 0), (0, 1.52, 0), 0.05)]
    for sign in (1.0, -1.0):
        shoulder = np.array([sign * 0.2, 1.4, 0])
        hand = shoulder + arm_reach * (np.array([sign * hand_at[0], hand_at[1], 0]) - shoulder)
        parts += [tube(shoulder, hand, 0.04), tube((sign * 0.1, 0.0, 0), (sign * 0.1, 0.9, 0), 0.07)]
    mesh = trimesh.util.concatenate(parts)
    return trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, 0.02), process=False)


def bind():
    found = np.tile(np.eye(4), (len(NAMES), 1, 1))
    found[:, :3, 3] = [JOINTS[name] for name in NAMES]
    return found


def parents():
    return np.array([NAMES.index(PARENTS[name]) if name in PARENTS else -1 for name in NAMES])


def nearest_bone_weights(points):
    """Each point on the bone (joint to its child, or the joint alone) nearest it, one-hot. The root has no bone (it
    stands on the floor under the hips)."""
    places = bind()[:, :3, 3]
    children = {PARENTS[name]: name for name in PARENTS if PARENTS[name] != "Root"}
    distance = np.full((len(points), len(NAMES)), np.inf)
    for joint, name in enumerate(NAMES):
        start = places[joint]
        end = places[NAMES.index(children[name])] if name in children else start
        line = end - start
        share = np.clip(((points - start) @ line) / max(line @ line, 1e-9), 0, 1) if line @ line > 0 \
            else np.zeros(len(points))
        distance[:, joint] = np.linalg.norm(points - (start + share[:, None] * line), axis=1)
    weights = np.zeros_like(distance)
    weights[np.arange(len(points)), distance.argmin(1)] = 1.0
    return weights


def fitted(target):
    source = body()
    mean = prop_rig.landmarks(prop_rig.sampled(source, 60000))
    fit = prop_rig.landmarks(prop_rig.sampled(target, 60000))
    return source, mean, fit


def test_skeleton_into_itself_comes_back():
    _, mean, fit = fitted(body())
    out, offsets = prop_rig.fitted_bind(bind(), NAMES, parents(), mean, fit)
    assert np.abs(out[:, :3, 3] - bind()[:, :3, 3]).max() < 0.005
    assert np.allclose(offsets[NAMES.index("LeftForeArm")], np.subtract(JOINTS["LeftForeArm"], JOINTS["LeftArm"]),
                       atol=0.005)


def test_weights_into_itself_come_back():
    source, mean, fit = fitted(body())
    weights = nearest_bone_weights(source.vertices)
    moved, matched_share, _ = prop_rig.transferred(source, weights, source, np.array(NAMES), fit)
    assert matched_share > 0.99
    assert (moved.argmax(1) == weights.argmax(1)).mean() > 0.99


def test_lowered_arms_turn_the_arm_bones():
    lowered = (0.42, 0.92)
    _, mean, fit = fitted(body(hand_at=lowered))
    out, offsets = prop_rig.fitted_bind(bind(), NAMES, parents(), mean, fit)
    shoulder = np.array([0.2, 1.4, 0.0])
    line = np.array([lowered[0], lowered[1], 0.0]) - shoulder
    line /= np.linalg.norm(line)
    for name in ("LeftForeArm", "LeftHand"):
        place = out[NAMES.index(name), :3, 3] - shoulder
        assert np.linalg.norm(place - (place @ line) * line) < 0.02, name
    forearm = np.subtract(JOINTS["LeftHand"], JOINTS["LeftForeArm"])
    assert abs(np.linalg.norm(offsets[NAMES.index("LeftHand")]) - np.linalg.norm(forearm)) < 0.005
    assert np.allclose(offsets[NAMES.index("LeftHand")], forearm, atol=0.005)


def test_inpainting_blends_the_unmatched_strip():
    grid = trimesh.creation.box(extents=(1.0, 0.01, 0.2))
    plane = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(grid.vertices, grid.faces, 0.03), process=False)
    plane.merge_vertices()
    x = plane.vertices[:, 0]
    weights = np.stack([(x < 0).astype(float), (x >= 0).astype(float)], 1)
    known = np.abs(x) > 0.25
    filled = prop_rig.inpainted(plane.vertices, plane.faces, weights, known)
    middle = np.abs(x) < 0.05
    assert np.all(filled[middle, 0] > 0.2) and np.all(filled[middle, 0] < 0.8)
    assert np.allclose(filled[known], weights[known])


def test_tuck_runs_under_the_garment():
    sleeve = tube((0, 0, 0), (0, -0.3, 0), 0.05)
    hand = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(sleeve.vertices, sleeve.faces, 0.02), process=False)
    hand.merge_vertices()
    open_hand = hand.faces[hand.triangles_center[:, 1] < -0.1]
    used, renumbered = np.unique(open_hand, return_inverse=True)
    points, faces = hand.vertices[used], renumbered.reshape(-1, 3)
    weights = np.tile([1.0, 0.0], (len(points), 1))
    turns = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    cuff = np.concatenate([np.stack([0.055 * np.cos(turns), np.full(48, height), 0.055 * np.sin(turns)], 1)
                           for height in np.linspace(-0.13, 0.0, 14)])
    bones = {0: [(np.array([0.0, -0.3, 0.0]), np.zeros(3))], 1: [(np.zeros(3), np.array([0.0, 0.3, 0.0]))]}
    whole = trimesh.creation.cylinder(radius=0.056, segment=[(0, -0.3, 0), (0, 0.0, 0)], sections=48)
    parents = np.array([1, -1])
    out_points, out_faces, out_weights = tucks.tucked(points, faces, weights, cuff, np.tile([0.0, 1.0], (len(cuff), 1)),
                                                      bones, whole, parents)
    band = out_points[len(points):]
    ring = np.unique(tucks.border_edges(faces))
    assert len(band) and abs(band[:, 1].mean() - (points[ring, 1].mean() + tucks.TUCK_LENGTH)) < 0.002
    assert np.linalg.norm(band[:, [0, 2]], axis=1).max() < 0.05 * (1 - tucks.TUCK_SHRINK) + 1e-6
    assert np.allclose(out_weights[len(points):], [0.0, 1.0])
    alone, _, _ = tucks.tucked(points, faces, weights, cuff + [0.0, 1.0, 0.0], np.tile([0.0, 1.0], (len(cuff), 1)),
                               bones, whole, parents)
    assert len(alone) == len(points)
    short = trimesh.creation.cylinder(radius=0.056, segment=[(0, -0.3, 0), (0, -0.09, 0)], sections=48)
    alone, _, _ = tucks.tucked(points, faces, weights, cuff, np.tile([0.0, 1.0], (len(cuff), 1)), bones, short,
                               parents)
    assert len(alone) == len(points)


def test_pokes_read_inside_and_outside():
    outer = trimesh.creation.box(extents=(0.1, 0.1, 0.1))
    heights = pokes.tuck_out(np.array([[0.0, 0.0, 0.04], [0.0, 0.0, 0.06]]), outer)
    assert heights[0] < 0 < heights[1]


def test_pokes_read_a_band_under_two_overlapping_parts_as_hidden():
    first = trimesh.creation.box(extents=(0.2, 0.1, 0.1))
    second = trimesh.creation.box(extents=(0.1, 0.1, 0.3))
    overlapping = trimesh.util.concatenate([first, second])
    heights = pokes.tuck_out(np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.3]]), overlapping)
    assert heights[0] < 0 < heights[1]


def test_pokes_hold_cloth_to_the_shipped_bodys_record():
    record = {"rest_crossings": 20, "verdict": {}, "clips": {"walking": {"most_crossings": 400},
                                                            "new": {"most_crossings": 30}}}
    pokes.against(record, {"body": "shipped.glb", "clips": {"walking": {"most_crossings": 5000}}})
    assert record["cloth_worse_than_shipped"] == ["new"] and not record["verdict"]["cloth_through_cloth"]


def test_a_leaning_body_is_stood_level():
    angle = np.radians(7.0)
    lean = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    points = prop_rig.sampled(body(), 60000) @ lean.T
    turn, scale, shift = prop_rig.stood(points, 1.75)
    stood = points @ turn.T * scale + shift
    head = stood[stood[:, 1] > 1.75 - 0.06 * 1.75].mean(0)
    feet = stood[stood[:, 1] < 0.08 * 1.75]
    assert abs(head[0] - (feet[feet[:, 0] > 0].mean(0)[0] + feet[feet[:, 0] < 0].mean(0)[0]) / 2) < 0.005


def test_thinning_keeps_the_parts_shut():
    sphere = trimesh.creation.icosphere(4, 0.2)
    part_of = (sphere.triangles_center[:, 1] > 0).astype(int)
    thin, thin_parts = prop_rig.decimated(sphere, part_of, 1500)
    assert thin.is_watertight and len(thin.faces) <= 1500
    border = sphere.vertices[np.intersect1d(sphere.faces[part_of == 0], sphere.faces[part_of == 1])]
    kept = thin.vertices[np.intersect1d(thin.faces[thin_parts == 0], thin.faces[thin_parts == 1])]
    assert len(border) == len(kept) and np.allclose(np.sort(border, 0), np.sort(kept, 0))


def test_a_band_takes_its_own_limbs_weights():
    parents = np.array([-1, 0, 0, 1, 2])  # hips; left and right shin; left and right foot
    garment = np.array([[0.05, 0.3, 0.0], [-0.02, 0.3, 0.0]])
    weights = np.zeros((2, 5))
    weights[0, 1], weights[1, 2] = 1.0, 1.0
    found = tucks.limb_weights(np.array([[0.0, 0.3, 0.0]]), np.array([3]), garment, weights, parents)
    assert found[0, 1] == 1.0


def test_a_hard_part_rides_one_joint_and_the_cloth_by_it_follows():
    names = ["Hips", "LeftShin", "LeftFoot"]
    boot = np.array([[0.1, 0.05, 0.0], [0.1, 0.2, 0.0]])
    assert prop_build.rigid_joint("boot_l", boot, np.ones((2, 3)), names) == "LeftFoot"
    cloth = np.array([[0.1, 0.21, 0.0], [0.1, 0.5, 0.0]])
    eased = prop_build.eased_to_hard(cloth, np.array([[0, 1.0, 0], [0, 1.0, 0]]), boot,
                                     np.array(["LeftFoot", "LeftFoot"], dtype=object), names, np.array([-1, 0, 1]))
    assert eased[0, 2] > 0.6 and eased[1, 2] == 0.0


def test_pokes_read_a_hard_parts_stretch():
    part = pokes.joins.Part("boot_l", np.array([[0, 0, 0], [1.0, 0, 0], [0, 1.0, 0]]), np.zeros((3, 4)),
                            np.eye(4)[:3], np.array([[0, 1, 2]]))
    edges = pokes.hard_edges([(part, "hard", None)])
    assert abs(pokes.stretch({id(part): part.points * 1.5}, edges) - 1.5) < 1e-9


def test_piping_is_cut_down_the_outside_of_a_limb():
    tube = trimesh.creation.cylinder(radius=0.05, height=0.6, sections=24)
    tube.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tube = tube.subdivide().subdivide()
    tube.apply_translation([0.1, 0.6, 0.0])
    places = {name: np.array(place, float) for name, place in JOINTS.items()}
    places.update(LeftLeg=np.array([0.1, 0.9, 0.0]), LeftShin=np.array([0.1, 0.6, 0.0]),
                  LeftFoot=np.array([0.1, 0.3, 0.0]))
    points, faces, weights, strip = piping.cut_piping(tube.vertices, tube.faces, np.ones((len(tube.vertices), 1)),
                                                      places)
    width = piping.PIPING_WIDTH
    middles = points[faces[strip]].mean(1)
    assert strip.any() and (middles[:, 0] > 0.14).all() and (np.abs(middles[:, 2]) < width / 2).all()
    area = np.linalg.norm(np.cross(*(points[faces[strip]][:, 1:] - points[faces[strip]][:, :1]).transpose(1, 0, 2)),
                          axis=1).sum() / 2
    assert abs(area - width * (0.6 - piping.LEG_RUN[0])) < 0.15 * width * 0.6, area


def test_a_flat_sheet_crosses_nothing():
    points = np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    assert pokes.self_crossings(points, np.array([[0, 2, 1], [0, 1, 3]])) == 0


def test_a_sheet_through_another_is_counted():
    lying = np.array([[-1.0, 0.0, -1.0], [1.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
    standing = np.array([[0.0, -1.0, 0.0], [0.0, 1.0, 0.2], [0.0, 1.0, -0.2]])
    points = np.concatenate([lying, standing])
    assert pokes.self_crossings(points, np.array([[0, 1, 2], [3, 4, 5]])) == 2


# --- the people route: regions, webs, limbs, the head, the correctives and the stretch -----------------------------

ROUTE_JOINTS = ["Root", "Hips", "Chest", "Neck1", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"]
TRUNK = route_bind.REGIONS.index(route_bind.TRUNK)
ARM = route_bind.REGIONS.index("LeftArm")


@pytest.fixture(autouse=True)
def props_home(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPS_HOME", str(tmp_path))


def facing(points, faces):
    corners = points[faces]
    return np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])[:, 2]


def test_a_lone_point_takes_its_neighbours_region():
    _, faces = grid(5, 2)
    labels = np.full(10, TRUNK)
    labels[4] = ARM
    assert (route_bind.majority(labels, route_bind.edges_of(faces)) == TRUNK).all()


def test_an_edge_whose_binds_jump_is_web_and_a_touching_seam_is_not():
    points = np.array([[0.0, 0, 0], [0.01, 0, 0], [0.02, 0, 0]])
    edges = np.array([[0, 1], [1, 2]])
    regions = np.array([TRUNK, ARM, ARM])
    places = np.array([[0.0, 0, 0], [0.05, 0, 0], [0.06, 0, 0]])
    assert route_bind.web_edges(points, edges, regions, places).tolist() == [True, False]
    touching = np.array([[0.0, 0, 0], [0.01, 0, 0], [0.02, 0, 0]])
    assert not route_bind.web_edges(points, edges, regions, touching).any()


def test_the_underarm_and_the_crotch_are_cut_but_the_shoulder_top_is_not():
    points = np.array([[0.0, 1.20, 0], [0.01, 1.20, 0], [0.0, 1.40, 0], [0.01, 1.40, 0], [0.0, 0.6, 0],
                       [0.01, 0.6, 0]])
    regions = np.array([TRUNK, ARM, TRUNK, ARM, route_bind.REGIONS.index("LeftLeg"),
                        route_bind.REGIONS.index("RightLeg")])
    edges = np.array([[0, 1], [2, 3], [4, 5]])
    found = route_bind.underarm_edges(points, edges, regions, {ARM: 1.40})
    assert found.tolist() == [True, False, True]


def grid(columns, rows):
    """A grid of points in the z = 0 plane, x along columns, its triangles wound to face +z."""
    points = np.array([[column * 0.01, row * 0.01, 0.0] for column in range(columns) for row in range(rows)])
    faces = []
    for column in range(columns - 1):
        for row in range(rows - 1):
            low, high = column * rows + row, column * rows + row + 1
            faces += [[low, low + rows, high], [high, low + rows, high + rows]]
    return points, np.array(faces)


def test_a_cut_is_closed_on_each_side_by_its_own_fan():
    points, faces = grid(6, 3)
    labels = np.where(points[:, 0] < 0.025, TRUNK, ARM)
    middle = (points[faces, 0].min(1) > 0.015) & (points[faces, 0].max(1) < 0.035)
    closed, middles = route_bind.closed(faces, labels, middle, len(points))
    assert sorted(len(ends) for ends in middles) == [3, 3]
    assert {labels[ends[0]] for ends in middles} == {TRUNK, ARM}
    kept = closed[:len(faces) - middle.sum()]
    assert (facing(points, kept) > 0).all()
    fans = closed[len(kept):]
    assert len(fans) == 2 * 3 and ((fans == len(points)) | (fans == len(points) + 1)).any(axis=1).all()
    grown = route_bind.with_middles(points, middles)
    assert np.allclose(grown[len(points):, 0], [0.02, 0.03]) or np.allclose(grown[len(points):, 0], [0.03, 0.02])


def test_a_limb_point_keeps_only_its_chain_and_its_shoulder():
    weights = np.full((2, len(ROUTE_JOINTS)), 1.0 / len(ROUTE_JOINTS))
    kept = route_bind.kept_to_limb(weights, np.array([ARM, TRUNK]), ROUTE_JOINTS)
    allowed = [ROUTE_JOINTS.index(name) for name in ("LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand")]
    assert np.allclose(kept[0].sum(), 1.0)
    assert np.allclose(np.delete(kept[0], allowed), 0.0)
    assert np.allclose(kept[1], weights[1])


def test_the_face_is_one_setting_and_keeps_the_made_face_by_default():
    """#26: until the owner decides, the body keeps the face Pixal3D made (its print from the close-up) and reads no
    old body; `drawn` drops the made face for the old drawn head, and refuses without the old body."""
    import argparse
    assert route_head.FACE == "made" and set(route_head.FACES) == {"made", "drawn"}
    document = {"materials": [{"name": "skin_head", "extras": {"role": "skin"}}, {"name": "hair", "extras": {"role": "hair"}},
                              {"name": "suit", "extras": {"role": route_build.pokes.GARMENT}}]}
    surfaces = [route_build.Surface(number, None, None, None, None) for number in range(3)]
    named = lambda face: [document["materials"][surface.material]["name"]  # noqa: E731
                          for surface in route_build.kept_surfaces(document, surfaces, face)]
    assert named("made") == ["skin_head", "hair"] and named("drawn") == ["hair"]
    with pytest.raises(SystemExit, match="--old"):
        route_build.drawn_head(argparse.Namespace(old=None), document, surfaces, None, None, [], None)


def test_the_collar_line_is_filled_round_the_neck():
    turns = np.linspace(-np.pi, np.pi, 8, endpoint=False) + 0.01
    border = np.stack([np.cos(turns) * 0.06, 1.45 + 0.01 * np.sin(turns), np.sin(turns) * 0.06], 1)
    line = route_head.collar_line(border, np.zeros(3), 1.5)
    assert len(line) == route_head.DIRECTIONS
    assert not np.isnan(line).any()
    assert line.min() >= 1.44 - 1e-9 and line.max() <= 1.46 + 1e-9


def test_points_under_the_collar_are_listed_last():
    points = np.array([[0.05, 1.50, 0.0], [0.05, 1.40, 0.0], [0.05, 1.55, 0.0]])
    order, tuck_from = route_head.tuck_order(points, np.full(route_head.DIRECTIONS, 1.45), np.zeros(3))
    assert order.tolist() == [0, 2, 1] and tuck_from == 2
    renumbered = route_head.reordered(order, np.array([[0, 1, 2]]))
    assert renumbered.tolist() == [[0, 2, 1]]


def test_the_neck_is_appended_under_the_old_head():
    old_points = np.array([[0.0, 1.5, 0.0], [0.01, 1.5, 0.0], [0.02, 1.5, 0.0], [0.01, 1.52, 0.0]])
    old_faces = np.array([[0, 1, 3], [1, 2, 3]])
    old_uv = np.array([[0.1, 0.1], [0.2, 0.2], [0.9, 0.9], [0.5, 0.5]])
    piece_points = np.r_[old_points, [[0.012, 1.45, 0.0]]]
    piece_faces = np.array([[0, 1, 3], [1, 2, 3], [4, 1, 0]])
    neck = route_head.Extension(piece_points, piece_faces, np.eye(5), old_points, old_faces, old_uv, np.eye(5)[:4])
    assert neck.found == 4 and len(neck.points) == 3
    assert neck.faces.tolist() == [[4, 5, 6]]
    assert np.allclose(neck.points, piece_points[[4, 1, 0]])
    assert neck.uv.tolist() == [[0.2, 0.2]] * 3


def test_the_lowest_band_of_the_drawing_is_painted_skin():
    picture = np.full((20, 20, 3), (200, 150, 120), np.uint8)
    picture[2:4, :] = 0
    points = np.array([[0.0, 1.50, 0.0], [0.01, 1.50, 0.0], [0.0, 1.51, 0.0], [0.0, 1.60, 0.0], [0.01, 1.60, 0.0]])
    faces = np.array([[0, 1, 2], [2, 3, 4]])
    uv = np.array([[0.0, 0.0], [0.5, 0.0], [0.0, 0.25], [0.6, 0.6], [0.9, 0.9]])
    painted = route_head.painted_neck(picture, points, faces, uv)
    assert (painted[2:4, :4] == (200, 150, 120)).all()
    assert (painted[2:4, 15:] == 0).all()


def test_the_scalp_is_drawn_under_the_hair():
    import trimesh
    hair = trimesh.creation.icosphere(subdivisions=2, radius=0.1)
    points = np.array([[0.0, 0.12, 0.0], [0.0, 0.05, 0.0]])
    moved, count = route_head.under_hair(points, hair.vertices, hair.faces, np.zeros(3), np.array([True, True]))
    assert count == 1
    assert np.linalg.norm(moved[0]) < 0.1 and np.allclose(moved[1], points[1])


def test_the_main_shapes_keep_offsets_made_of_few_directions():
    rng = np.random.default_rng(0)
    directions = rng.normal(size=(2, 30))
    stacked = (rng.normal(size=(40, 2)) @ directions).astype(np.float32)
    shapes, weights, kept = route_build.principal_shapes(stacked, 2)
    assert kept > 0.999
    assert np.allclose(weights @ shapes, stacked, atol=1e-4)


def test_the_longest_edge_of_each_triangle():
    points = np.array([[0.0, 0, 0], [3.0, 0, 0], [0.0, 4.0, 0]])
    assert route_stretch.longest_edges(points, np.array([[0, 1, 2]])).tolist() == [5.0]


def test_a_boots_shaft_follows_the_shin_and_its_sole_the_foot():
    names = ["LeftFoot", "LeftShin", "RightFoot", "RightShin"]
    bind = np.tile(np.eye(4), (4, 1, 1))
    bind[0, :3, 3], bind[1, :3, 3] = [0.1, 0.06, 0.0], [0.1, 0.48, 0.0]  # left ankle and knee
    bind[2, :3, 3], bind[3, :3, 3] = [-0.1, 0.06, 0.0], [-0.1, 0.48, 0.0]
    # The left boot: its shaft's top over the ankle, its toe cap ahead of it, its heel under it, its sides graded.
    points = np.array([[0.1, 0.23, 0.0], [0.1, 0.03, 0.15], [0.1, 0.0, -0.04], [0.1, 0.12, 0.06]])
    weights = np.zeros((4, 4))
    weights[:, 0] = 1.0
    document = {"materials": [{"extras": {"role": "hard"}}]}
    tops = route_build.shaft_tops(document, [route_build.Surface(0, points, None, weights, None)], names, bind)
    assert tops == {(0, 1): 0.23}
    found = route_build.shafted(points, weights, bind, tops)
    assert found[0, 1] == 1.0 and found[1, 0] == 1.0 and found[2, 0] == 1.0
    assert 0.0 < found[3, 1] < 1.0 and np.allclose(found.sum(1), 1.0)
    shoe = points * [1.0, 0.3, 1.0]  # its top 7 cm up: not past SHAFT_FROM over the ankle, so nothing bends
    assert route_build.shaft_tops(document, [route_build.Surface(0, shoe, None, weights, None)], names, bind) == {}


def test_a_web_bridging_the_legs_fails_the_stretch_check():
    # One triangle from the left thigh to the right one, 4 cm wide at rest; the legs part 0.21 m in the stride.
    rest = np.array([[0.02, 0.7, 0.0], [-0.02, 0.7, 0.0], [0.0, 0.72, 0.0]])
    faces = np.array([[0, 1, 2]])
    bind = route_stretch.longest_edges(rest, faces)
    posed = rest + np.array([[0.105, 0.0, 0.0], [-0.105, 0.0, 0.0], [0.0, 0.0, 0.0]])
    most, triangle = route_stretch.grown(posed, bind, faces)
    assert triangle == 0 and np.isclose(most, 0.21)
    assert most > route_stretch.MOST_METRES
    assert route_stretch.grown(rest, bind, faces)[0] == 0.0


def test_the_body_under_a_cut_web_is_drawn_inside_in_the_cut_garments_cloth():
    base_points, base_faces = grid(20, 3)
    base_weights = np.tile(np.eye(len(ROUTE_JOINTS))[2], (len(base_points), 1))
    sleeve = route_build.Surface(7, np.full((2, 3), 5.0), None, None, np.zeros((0, 3), int))
    torso = route_build.Surface(3, np.full((3, 3), 5.0), None, None, np.zeros((0, 3), int))
    bound = route_bind.Bound(np.zeros((5, 3), int), np.tile([1.0, 0.0, 0.0], (5, 1)), base_points)
    welded = {"numbers": np.array([0, 1, 2, 3, 4]), "starts": [0, 2], "web": {(2, 3)}, "bound": bound}
    correctives = {"clip_walking": np.ones((4, len(base_points), 3), np.float32)}
    over = route_build.Surface(9, base_points + [0.0, 0.0, 0.01], None, None, base_faces)  # the cloth 1 cm out
    layer = route_build.under_layer([sleeve, torso, over], welded, base_points, base_faces, base_weights,
                                    correctives, ["walking"])
    assert layer.material == 3
    inside = int(np.sum(base_points[::3, 0] < route_build.UNDER_REACH))  # grid columns (1 cm apart) under the reach
    assert len(layer.faces) == (inside - 1) * 2 * 2
    assert np.allclose(layer.points[:, 2], -route_build.UNDER_INSET)
    assert layer.points[:, 0].max() <= route_build.UNDER_REACH + 1e-9
    assert layer.offsets["walking"].shape == (4, len(layer.points), 3)
    assert route_build.under_layer([sleeve, torso, over], {**welded, "web": set()}, base_points, base_faces,
                                   base_weights, correctives, ["walking"]) is None


def test_cloth_next_to_a_skin_part_rides_its_weights_and_takes_no_correctives():
    """2026-10-22: the astronaut's made face went 10 mm through the helmet bent with the neck, and the base's
    correctives moved the trouser hem riding the boot into the boot."""
    parents = np.array([-1, 0, 1, 2, 1, 4, 5, 6])  # ROUTE_JOINTS: Root, Hips, Chest, Neck1, LeftShoulder, LeftArm, ...
    face = np.zeros((1, len(ROUTE_JOINTS)))
    face[0, [2, 3]] = [0.2, 0.8]
    neck, arm = (np.eye(len(ROUTE_JOINTS))[number] for number in (3, 5))
    places = np.array([[0.0, 0, 0.02], [0.0, 0, 0.5], [0.0, 0, 0.03]])
    target, share = route_build.skin_share(places, np.stack([neck, neck, arm]), (np.zeros((1, 3)), face), parents)
    assert share[:, 0].tolist() == [1.0, 0.0, 0.0]  # held; out of reach; on an arm, not the face's family
    assert np.allclose(target[0], face[0])
    bound = route_bind.Bound(np.zeros((3, 3), int), np.tile([1.0, 0.0, 0.0], (3, 1)), np.zeros((1, 3)))
    moves = route_build.clip_offsets({"clip_walking": np.ones((2, 1, 3), np.float32)}, ["walking"],
                                     {"bound": bound, "eased": share[:, 0]})["walking"]
    assert np.allclose(moves[:, 0], 0.0) and np.allclose(moves[:, 1:], 1.0)
    _, none = route_build.skin_share(places, np.stack([neck] * 3), (np.zeros((0, 3)), np.zeros((0, len(ROUTE_JOINTS)))),
                                     parents)
    assert not none.any()


def test_the_body_under_a_cut_web_is_not_drawn_where_it_would_show_through_the_cloth():
    """2026-10-22: the base stood out of the astronaut's slim suit and its under layer showed as white patches."""
    base_points, base_faces = grid(20, 3)
    base_weights = np.tile(np.eye(len(ROUTE_JOINTS))[2], (len(base_points), 1))
    torso = route_build.Surface(3, np.zeros((2, 3)), None, None, np.zeros((0, 3), int))
    bound = route_bind.Bound(np.zeros((2, 3), int), np.tile([1.0, 0.0, 0.0], (2, 1)), base_points)
    welded = {"numbers": np.array([0, 1]), "starts": [0], "web": {(0, 1)}, "bound": bound}
    tight = route_build.Surface(9, base_points - [0.0, 0.0, 0.002], None, None, base_faces)  # 2 mm inside the base
    assert route_build.under_layer([torso, tight], welded, base_points, base_faces, base_weights, None, []) is None


def test_the_route_reads_the_body_node_its_outfit_named():
    """2026-10-22: one body a look, its outfit `made`; the route looked for a node named `work` and found none."""
    document = {"nodes": [{"name": "Person"}, {"name": "far", "mesh": 0, "skin": 0},
                          {"name": "made", "mesh": 1, "skin": 0}]}
    assert route_build.body_node(document) == "made"
    with pytest.raises(SystemExit):
        route_build.body_node({"nodes": [{"name": "far", "mesh": 0, "skin": 0}]})
