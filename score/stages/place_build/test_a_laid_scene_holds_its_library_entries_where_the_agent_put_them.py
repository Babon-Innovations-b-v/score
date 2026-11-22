"""Invariant: the placing agent's scene holds each library entry it lays, where it lays it: a kit piece referenced
from its own copy under the place's assets, in metres in a y-up stage, its spot and turns snapped onto the grid; a
surface bound over the model's own colour (a variant as the library makes it, a recipe in the palette colour asked,
refused without one), or on one named part alone while the rest keeps the whole look; a glTF-only model converted with a
part a material, each wearing its own bake (its base colour map beside it, read by the mesh's texture coordinates),
a take's finished model laid before its raw one; a ground disc laid as the ground; a character dressed in its made body (its far one hidden) and held still in its clip, its own
SkelRoot kept; a ground marked as the ground; the dome shell's glass skin, curved ribs and deck as three parts at its radius;
a batch of steps run in one call, a refused one named while the rest go on; a lamp where it is laid; an entry with no
USD refused by name, a removed object gone; a real terrain's heightfield (fine posts near its centre, wider out, its gaps
filled) laid as the ground with its building pads levelled to the laid height and the ground beyond untouched; a sky
laid as the place's own Environment with a sun shining from where it is asked; the place's palette (a scene's surface
library) laid as a recipe spec on a look at its wear and dirt; a dome cut at an opening (glass and plinth) and a tunnel
with a doorway in its end wall (its rim round on the tube's circle, never stepped), its skin trimmed by the dome it
joins and solid below its glass; a model's glow layer
laid with it as a part; a stair core whose treads look up (the walkers' floor reads them as floor) and rise no more
than a knee, its flat's doorway cut through its back wall, its facade closed onto the shaft and its faces flat-shaded, a street door's doorway cut in its lobby's facade; a street's block turned a quarter hollowed where a neighbour place is seated in it (its boxes cut, its parts, pose and role kept, the shop's table and lamp and the fittings left with no wall taken out, a door leaf, a sign on what is left and a neighbouring block reaching in kept); a recipe's glass laid from the library see-through at the method's opacity; every packaged picture's sides a multiple of four; an airlock packaged with each door's hinge, opening, mark and sides and its chamber's inner and outer door and air, each pressure door swinging to its high-pressure side, and an airlock built from blocks given its chamber and doors by their marks, its plug door sliding aside, a door a walker swings over time packaged shut with its door block and any other keyed object left out; a final render at 1920x1080; a film's path held on the concept's view, round a wall at eye height and clear of it, easing to a stop; a named view listed beside the
concept's for the render; and the compare measures the render's silhouette against the concept's object masks (overlap, each object's cover) and the
colour difference of the two pictures, and draws them side by side; and a review of a region holds its laid objects
(never the ground or the sky), each dome shell structure a compartment, a door's eye-height view, a plan seen
straight down under its cut with +x right and +z down, and a physics fault boxed in red and named on the plan; and
the laid scene as a piece list (score.scene v2, no Blender: each library piece once by its address and digest, the
made geometry as untextured GLBs a mesh a part, each copy's parts' looks, its check sound and refusing a stale digest,
a withdrawn entry, a changed made file and a part with no look) and
the laid scene packaged for an engine (score.scene v1, package.py's check sound) with every copy filling its laid box,
copies in one surface one object, a glTF model laid unchanged its own library glTF, its looks as PBR (a palette
recipe baked into its own maps, on a ground one seamless tile; glass as transmission), its colliders from the
physics check's roles and the place's environment (its night, sun and grade), its bake run a few maps of one object at
a time and a stopped bake resumed from the maps it finished, a changed object's maps baked again. A wall the camera cuts (place.json `cut`) is
no solid to the film's camera and still one to the walkers, cut in the concept's view and a view made a cut view while
an outside view sees it standing, and a cut stair core's front wall is written to its own file. A still draws the place
without the walkers' layer. A Moon place's physical sky (sky-at) holds what overhead.py says is overhead at its
site and time (the light stage's own gate finds no fault), a sky laid before cleared, each body in its library face
or named missing when the library holds none, black under the airless sky at the brightest light's exposure; a body
with air is refused.

Breaks that turn this red (each applied once and seen red, then reverted):
- place_build.posed: the rotate op left out -> the turned piece's box stays unturned
- place_build.snap: `on_grid` on the height too -> the lifted piece drops to the grid
- place_build.tinted: the colour set on the diffuse input though a map feeds it -> the sand's map keeps no tint
- place_build.look_shader: `strongerThanDescendants` made `weakerThanDescendants` -> the piece's own look wins
- place_build.usd_file: the first file taken whatever its role -> a record-only entry is laid
- place_build.rebind: the whole look left off the unnamed parts -> the crate's lid keeps its baked green
- place_build.laid_reference: the prim defined as an Xform -> the character's prim is an Xform, not its SkelRoot
- place_build.dressed: WORN's "made" made "far" -> the far body shows and the made one is hidden
- gltf.part_name: the material's name dropped (`part_<n>` always) -> the glTF's parts lose their names
- gltf.look: the maps left out -> the door part wears no base colour map (its bake is lost)
- place_build.finished_first: `-final` not ranked first -> the take's raw model is laid
- place_build.ground: the ground mark left False -> the laid disc is no ground
- dome_shell.ribs: the rib lifted inward (`- out`) -> the dome's box stays inside its radius
- dome_shell.plinth: its faces wound as before (inward) -> the holed dome's base ring has negative volume (an engine
  drew its inside, the ring gone in 2099's Unity)
- dome_shell.swept: `turned` ignored -> the oculus ring and collars have negative volume
- place_build.rested: the lift's sign flipped -> the shelf on the table sinks a metre under it
- dome_shell.hoop_ribs: the hoop lifted inward (`- out`) -> the tunnel's box stays inside its radius
- place_build.ground_points: the key made of the References handle's repr -> the ground is read again for a stone
- place_build.ground_height: the nearest point's x read for its height -> the stone floats far off the slope
- place_build.ground_height: no face searched (the nearest points' weighted height) -> the stone stands off the
  slope's plane by more than a millimetre
- place_build.batch: a refused step stops the batch -> the step after it is never laid
- measure.coverage: `shape & silhouette` made `shape` -> the uncovered object reads covered
- relief.graded_axis: FAR_GROWTH left off (every post 1 m) -> the far posts are not wider than the near ones
- relief.filled: the gap left NaN -> the terrain holds a NaN height
- relief.padded_file: the pad's share inverted (`keep = eased`) -> the pad keeps its slope, the far ground goes flat
- relief.turned_pads: the turn's sine signs swapped -> the pad lands off the dome's spot on the turned terrain
- place_build.sun_frame: `towards` negated -> the sun shines up from under the ground
- place_build.sky: the turn left off the dome -> the sky dome stays unturned
- place_build.sky: the exposure left off -> the stopped-down day renders at the sky entry's own exposure
- render.views: the named views left out -> the inside view is not rendered
- render.views: `review` kept True when final -> the final render runs at the review's samples
- dome_shell.chamfered_box: the outward flip dropped -> a block's solid has negative volume (faces inward)
- place_build.blocks: the structure role not written -> a building's blocks read as a loose prop to the check
- place_build.put: role and support not written -> a window flush on its wall reads as a floating prop
- place_build.night: the exposure left off -> the night renders at the day's exposure
- place_build.made_by_haze: unread -> the mist's body and look name no library algorithm
- place_build.made_by_library: unread -> the sky's sun, Environment and disc name no library algorithm, the disc's
  look no library recipe
- scene_package.environment_of: the sun read from Lights/sun alone -> the sky-at place's package has no sun
- place_build.sky_at: the sky laid before left (SKY_PATHS not cleared) -> the old Lights/sun stands beside the Sun
- place_build.library_face: the withdrawn state not read -> Mars's ball is painted from its withdrawn face
- place_build.turned: the turn left off -> the light stage's gate finds the Sun and Earth off overhead.py's ways
- place_build.sky_at: exposure left at 1 -> the Moon's noon renders 1 where a white face square to the Sun reads 1
- place_build.airless: every body taken as airless -> a Mars site is laid under a black sky
- dome_shell.skin: the opening's faces kept instead of dropped -> the holed dome's glass closes its opening
- dome_shell.end_wall: the doorway a third narrower -> the end wall stands in the doorway
- dome_shell.on_circle: a corner kept where it lies -> the end wall's rim steps out past the tube's circle
- dome_shell.tube_skin: the trim inverted -> the hall's skin stands inside the dome it joins
- dome_shell.onto_trims: no point slid (the face kept or left by its middle) -> the hall's end steps along the glass
- dome_shell.tube_sides: no lower wall split off -> the hall's glass reaches its deck
- dome_shell.ribs: the oculus ignored (meridians to the top) -> a rib crosses the dome's crown
- dome_shell.strips: the band stood outward (`inward` negated) -> the light strip hangs outside the glass
- dome_shell.plinth: the asked height left off (BASE_HIGH always) -> the deep base ring stays 0.22 m
- place_build.surface: the palette spec left off the look -> the panel's look carries no recipe spec
- stair_core.front_windows: the curtain's head left at the storey line (no `- SLAB`) -> the curtain front's glass runs
  into the slab over it
- film.route: every leg straight, never walked -> the lane's film finds no clear way round its wall
- film.distances: the hold drifting at 0.1 m a frame -> the film does not open still on the concept's view
- film.rounded: the cut corners kept unchecked -> a frame stands nearer the wall than the clearance
- film.distances: the walk's speed kept to the end -> the camera does not slow to a stop
- film.place_scenes: `standing.get(name, laid.meshes[name])` -> `laid.meshes[name]` -> the open door blocks the camera
- place_build.palette_spec: the place's wear and dirt replaced by 0 -> the spec's wear is not the palette's
- stair_core.outward: `volume > 0` made `volume < 0` -> the treads look down
- stair_core.holed: the holes left out -> the back wall stands in the flat's doorway
- stair_core.core: the front kept when `cut` -> the cut-away still stands behind its front wall
- stair_core.front_alone: `front(...)` left out -> the cut core's front wall is written nowhere
- film.place_scenes: the `cut` left unread -> the camera runs into the wall it sees through
- place_build.camera_cut: the scene's prim left unasked -> a cut of an object the scene does not hold is listed
- render.views: every view given place.json's cut -> the outside view sees through the cut wall
- render.views: a named view's `cut` left unread -> the view made a cut view sees the wall standing
- stair_core.core: the second block kept with `one_block` -> a flats' block stands past the shaft's far wall
- stair_core.block: the corner pier left out -> the slot between the facade and the shaft's side wall stays open
- stair_core.block: `holes + door` -> `holes` -> the street door's doorway stands walled in the lobby's facade
- stair_core.block: the ground window kept with `street` -> a pane stands across the street door's doorway
- place_build.rewritten: the open layer's content not taken (`write(path)` over it) -> a cut core laid again in one
  batch fails: USD makes no new layer where its front's is open
- dome_shell.written: `flat` ignored -> the stair core carries no faceVarying normals (it renders pillowed)
- render.views: FINAL_SIZE left off -> the final render keeps the concept's aspect
- render.libraries: the libs/ default dropped (SCORE_BLENDER_LIBS alone) -> a box without the variable starts a
  Blender that cannot find libSM (exit 127), and the failure names no fix
- place_build.layered: the layer mark left off -> the monitor's glow is no part and its screen takes no surface
- measure.lab: a and b read unsigned -> the concept's blue reads yellow (b over 0)
- scene_package.enclosure_at: the hull's planes read inward (`>= -1e-6`) -> the lock's doors open between nothing and
  it is no chamber
- scene_package.doors_of: `None in door["between"]` read for inner doors too -> the porch door reads as an outer door
- scene_package.air_of: the deck's top left off (the hull from the skin's foot) -> the lock's air is past its segment
- scene_package.opening_of: the cap part not read -> the hatch in the lock's end wall reads as in no end wall
- scene_package.locks_of: `toward` left the chamber's way for inner doors too (no `-into`) -> the lock's inner door
  swings into the chamber like a closet door, not out to the porch
- scene_package.locks_of: the marked doors left unread (marked_locks empty) -> the blocks-built cell is no chamber
- scene_package.door_block: every door written a hinge -> the cell's plug door has no slide
- scene_package.moving_door: every keyed object taken for still (False) -> the lock's swinging inner door is
  left out as moving, so it lays no door
- scene_package.moving_door: the role read off (every keyed object a door) -> the keyed fan is packaged
- place_build.from_library: a sublayer the entry does not hold kept -> the lane's scene names a walkers layer its
  folder lacks
- place_build.from_library: `entries = localised(folder)` -> `entries = []` (and its key) -> the lane's box names the
  library on USD's search path and opens as nothing
- place_build.blocks: the role always structure -> the knob reads a structure
- place_build.blocks: `None if ground else support` -> `None` -> the couplet is a mount on no wall
- ready.inward: shells and connectors alone -> the plug set in the cell's walls of blocks is set in none
- scene_package.chamber_air: a chamber's air only its named object's hull -> the cell whose doors name its back
  wall holds no air, so no chamber
- place_build.look_shader: a recipe look keeps the references laid before it -> the regolith's ground surface still
  composes under its palette paint
- place_build.door: a held mark of another type kept -> the plug's old bool score:opens refuses the string mark
- place_build.door: the score:move mark left off -> the cell's plug door swings, the walkers' leaf is not slid aside
- review.region_of: the ground mark not read (`not item["ground"]` dropped) -> the terrain and sky join the region
- review.compartments_of: the dome shell address test dropped -> the wall is a compartment
- review.projected: the up axis negated -> the plan's +z lands up, the aim's point off the middle
- review.views_of: the plan's near cut at the floor (CUT left off) -> the plan's cut is not CUT over the floor
- review.boxed_faults: the fault's name test inverted -> no red box on the floating crate
- rainfall.falling: the jump back left out -> the rain is not back at its top a period on
- rainfall.falling: the lean left out of the slide -> the streaks fall straight down across their own lean
- rainfall.landings: ceil taken as floor -> a splash shows a frame before its drop reaches the ground
- rainfall.shown: the frame's mesh left at the ground -> splashes stand where no drop has landed
- ground_tracks.rut_rows: LIFT left off -> the ruts' floor sinks into the ground
- place_build.remove: Effects not looked in -> the removed ruts stay laid
- place_build.usd_file: an effect's `usd` root unread -> the wisp lays its clip.usdc, not its emitter
- place_build.usd_file: a model's `usd` root unread (ROOTED_KINDS the effect alone) -> the adopted crate lays its
  base payload, not its root
- place_build.layered: a layer taken from any folder (the same-folder test dropped) -> the crate's payload
  sm_crate_01_geo is laid as its layer `geo`
- library.replaced_end: the chain left unfollowed (`return address` at once) -> the retired crate is refused
  withdrawn, not laid as the adopted crate
- place_build.put: an effect laid under Objects -> the wisp is a solid object with no role
- place_build.hold: the pose's rotations not written -> the walker's hips keep their clip's turn
- place_build.held_prop: the hold frame left out (the joint's transform alone) -> the stub sits on the hips, not
  0.1 m along their turned x
- place_build.held_prop: the turn decomposed X, Y, Z (not rotateXYZ's Z, Y, X reversed) -> the stub's up is off
- place_build.remove: place.json's cut left as it was -> a removed awning stays listed in the cut
- place_build.object_prim: Effects not looked in -> the ruts take no surface ("no object ruts")
- scene_package.copy_frame: every copy kept whole (no evenness test) -> a stretched copy fails the package check
- scene_package.taken_down: every picture kept at its own size -> a 64 texel map is packaged over HELD_TEXELS
- scene_package.pictures_held: no picture held once (`by_bytes` unread) -> two of an object's images hold one picture
- scene_package.pictures_read_as: every map read as linear -> the base colour shares its picture with linear maps
- scene_package.held_image: unread in pbr (every map held whole) -> the dune's look holds its sand map at 64
- scene_package.write: every character made before any is written (character_objects, as before) -> the leader is
  written after the crowd's people are made (the square's 1,260 people held at once, past 14 GB)
- scene_package.gprim_pieces: the cube's own transform left out (identity) -> the crate's model misses its laid box
- scene_package.look_name: the look's own prim name -> the two steel walls are two objects
- scene_package.entry_glb: never reused (None) -> the cabinet is converted, not its library glTF
- scene_package.face_looks: the parts' subsets ignored -> the crate's lid top has no steel look
- scene_package.pbr: the map's tint left off -> the sand's base colour is white
- scene_package.gprim_pieces: the tile ignored (the mesh's own st) -> the dune has no tiled coordinates
- scene_package.mass_of: the scale's cube left off -> the doubled box weighs 12.5 kg, not 100
- place_build.recipe_marked: the spec's opacity left off the look -> the plank's palette glass is packaged OPAQUE
- place_build.palette_spec: the method's recipe defaults not under the place's copy -> the porthole's spec carries no
  opacity (a palette taken before glass carried it lays opaque glass)
- scene_package.glass_of: the tint left the look's colour -> the tunnel's glass passes (0.5, 0.5, 1), not (0.9, 0.9, 1)
- scene_package.attached: the normal map left off -> the panel's baked maps carry no normal texture
- place_build.look_shader: a recipe entry's settings alone (the method's defaults unread) -> the panel's recipe glass
  laid from the library carries no opacity (opaque in the package: the stairwell's glass, 2099 2026-11-22)
- scene_package.held_image: its sides left as halved (no BLOCK_TEXELS) -> the dune's 62 texel sand is held at 31
- place_build.taken_with: a fitting kept whatever wall is left (FITTING_REACH unread) -> the hollowed block's rack and
  the wash on it stay
- place_build.taken_with: an object taken out by its middle alone -> the neighbouring block reaching out of the region
  (its middle in it) goes whole
- scene_package.environment_of: the exposure left off -> the night's 2.5 reads 1.0
- scene_package.pbr: `not draft` left off -> the draft package asks the baker for the panel's maps
- scene_package.written_scene: the DRAFT mark left off -> the draft package's scene.json carries no draft
- scene_package.pbr: the ground's tile left None -> the regolith's recipe is unwrapped, no tile baked
- scene_package.blender_baked: every map baked again (marks ignored) -> the resumed bake asks the stopped one's
  finished panel map 0 again
- scene_package.map_keys: the object's buffer left out of the key -> the changed panel's maps 0 and 1 are kept
- scene_package.batches: one run for all the maps -> a run holds the maps of both objects, past BATCH
- scene_package.blender_baked: its runs one after another (SIDE_BY_SIDE ignored) -> the three objects' runs never
  hold the card two at once
- render.queued: `card_gb` and `memory_gb` ignored -> a bake run asks the queue for render.CARD_GB and no memory
- render.still_stage: the walkers' layer kept -> the still's scene holds walker_one
- render.still_stage: its paths left unanchored -> the still under render/ misses every laid object's model
- scene_package.write: the whole package folder removed -> the stopped bake's maps are gone before the bake
- scene_package.gprim_pieces: a mesh with no normals of its own shaded flat -> the holed panel's points carry many
  normals each, not Blender's one smooth normal
- scene_package.ground_albedo: the picture's sRGB mean taken as linear -> the regolith's albedo reads 0.5, not 0.216
- scene_package.packaged: the grade left undrawn -> the environment names no grade picture
- scene_package.attached: a picture named by its uri -> the panel's images are files, not its buffer's (glTFast drew
  every baked part as bare metal)
- scene_package.distant: the USD intensity as the strength -> the moon is 0.01, not the render's 0.04
- scene_package.unwrapped: a sliver xatlas charts on no map left out -> the sliver beside the square is lost (2 of 3)
- skinned.character_glb: the Skeleton's frame (`Turned`) left out of the inverse binds -> the leader's skin lies off
  UsdSkel's and its check fails
- skinned.animation_of: the blend shape weights left out -> the leader's mesh node keys no weights
- skinned.moves_of: the walk left out -> node 0 keys no translation
- skinned.sample_times: the clip kept whole (no round) -> the leader's clip lasts two rounds
- skinned.copies_of: the prototype's transform taken for the instance's -> the crowd copies stand at one spot
- scene_package.densities: the eyes ignored (DENSITY on every face) -> the panel seen from 100 m is baked at 24
  texels a metre, not 16
- scene_package.densities: no eye within reach taken for no eyes given -> the panel no eye comes near (the square's
  far shore) is baked at 24 texels a metre, not 16
- scene_package.subdivided: the mesh returned uncut -> the 12 m panel's faces each need more than a map (refused)
- scene_package.atlas_of: packed at a fixed resolution (`packing.resolution = LARGEST`) -> the 1 m tile's map is
  LARGEST wide, not its charts' size
- scene_package.deadline: `exit=True` left off -> the stuck step runs on past its time and the package goes on
- render.queued: `seconds` dropped -> a bake run's Blender has no timeout
- pieces.library_address: every copy taken for made (no library piece) -> kerb2 is a made piece of its own, not
  box_piece
- package.piece_problems: the digest left unchecked -> the box piece's stale digest passes the check
- scene_package.mass_of: the asset's authored mass left unread (usd_physics.authored_mass skipped) -> the adopted
  prop weighs its record's 3 kg, not its asset's 1.5496 kg times its scale cubed (#155)
- scene_package.metal_rough: the texture output read left off (`channel(found[0], "r")`) -> the adopted look's
  roughness and metal are its ORM map's occlusion (red), not its green and blue (#155)
"""
import json
import pathlib

import trimesh

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, UsdSkel, Vt

from score.stages import place_build
from score.stages.place_build import film, measure, ready, relief, render, review, stair_core


def library(root, files):
    """A small library: a kit piece (a 1 x 2 x 0.5 m box in its own baked green), a variant surface and a recipe,
    a lamp, and a record-only kit entry; its files under `files` by their references."""
    def entry(kind, entry_id, named, provenance=None):
        folder = root / "entries" / kind / entry_id / "1"
        folder.mkdir(parents=True)
        folder.joinpath("entry.json").write_text(json.dumps({
            "schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "kind": kind, "id": entry_id,
            "version": 1, "files": {name: {"role": role} for name, (role, _) in named.items()},
            "provenance": provenance or {}}))
        for name, (_, text) in named.items():
            target = files / f"{kind}/{entry_id}@1/{name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            if text is not None:
                target.write_text(text)
    piece = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(piece, UsdGeom.Tokens.y)
    root_prim = UsdGeom.Xform.Define(piece, "/box")
    piece.SetDefaultPrim(root_prim.GetPrim())
    cube = UsdGeom.Cube.Define(piece, "/box/geo")
    cube.AddTranslateOp().Set(Gf.Vec3d(0.5, 1.0, 0.25))
    cube.AddScaleOp().Set(Gf.Vec3f(0.5, 1.0, 0.25))
    cube.CreateSizeAttr(2.0)
    own = UsdShade.Material.Define(piece, "/box/baked")
    baked = UsdShade.Shader.Define(piece, "/box/baked/surface")
    baked.CreateIdAttr("UsdPreviewSurface")
    baked.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 1.0, 0.0))
    own.CreateSurfaceOutput().ConnectToSource(baked.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(cube.GetPrim()).Bind(own)
    lid = UsdGeom.Mesh.Define(piece, "/box/lid")
    lid.CreatePointsAttr(Vt.Vec3fArray([(0, 2, 0), (1, 2, 0), (1, 2, 0.5), (0, 2, 0.5)]))
    lid.CreateFaceVertexCountsAttr([3, 3])
    lid.CreateFaceVertexIndicesAttr([0, 1, 2, 0, 2, 3])
    UsdGeom.Subset.CreateGeomSubset(lid, "top", UsdGeom.Tokens.face, [0], "materialBind")
    rim = UsdGeom.Subset.CreateGeomSubset(lid, "rim", UsdGeom.Tokens.face, [1], "materialBind")
    UsdShade.MaterialBindingAPI.Apply(rim.GetPrim()).Bind(own)  # a part in its own baked green
    entry("kit", "box_piece", {"piece.usda": ("usd", piece.GetRootLayer().ExportToString()),
                               "piece.json": ("record", "{}")})
    entry("kit", "plan_only", {"plan.json": ("record", "{}")})
    glb = tmp_glb(root.parent)
    entry("model", "cabinet", {"cabinet.glb": ("gltf", None)},  # its parts painted from the library (finished/)
          {"made_with": [{"by": "score", "what": "split, painted from the library surfaces and baked"}]})
    (files / "model/cabinet@1/cabinet.glb").write_bytes(glb)
    entry("take", "cup", {"cup.glb": ("gltf", None), "cup-final.glb": ("gltf", None)})
    for name in ("cup.glb", "cup-final.glb"):
        (files / f"take/cup@1/{name}").write_bytes(glb)
    entry("character", "walker", {"character.usda": ("usd", character())})
    emitter = ('#usda 1.0\n(\n defaultPrim = "smoke"\n)\ndef Xform "smoke"\n{\n string score:effect:kind = '
               '"smoke_wisp"\n}\n')
    entry("effect", "wisp", {"clip.usdc": ("usd", "a baked clip"), "effect.usda": ("usd", emitter)})
    written = root / "entries/effect/wisp/1/entry.json"
    written.write_text(json.dumps(dict(json.loads(written.read_text()), usd={"root": "effect.usda"})))
    turned = {"hips": {"rotation": [0.7071068, 0.0, 0.7071068, 0.0]}}  # a quarter turn about up
    entry("character", "hold", {"pose.json": ("record", json.dumps({"joints": turned, "hold": {
        "joint": "hips", "translate": [0.1, 0.0, 0.0], "rotation": [0.7071068, 0.7071068, 0.0, 0.0]}}))})
    variant = ('#usda 1.0\n(\n defaultPrim = "steel"\n)\ndef Material "steel"\n{\n token outputs:surface.connect = '
               '</steel/surface.outputs:surface>\n def Shader "surface"\n {\n  uniform token info:id = '
               '"UsdPreviewSurface"\n  color3f inputs:diffuseColor = (0.3, 0.3, 0.4)\n  token outputs:surface\n }\n}\n')
    entry("surface", "steel", {"material.usda": ("usd", variant), "surface.json": ("record", "{}")})
    mapped = ('#usda 1.0\n(\n defaultPrim = "sand"\n)\ndef Material "sand"\n{\n token outputs:surface.connect = '
              '</sand/surface.outputs:surface>\n def Shader "colour"\n {\n  uniform token info:id = "UsdUVTexture"\n'
              '  asset inputs:file = @./colour.jpg@\n  float3 outputs:rgb\n }\n def Shader "surface"\n {\n'
              '  uniform token info:id = "UsdPreviewSurface"\n  color3f inputs:diffuseColor.connect = '
              '</sand/colour.outputs:rgb>\n  token outputs:surface\n }\n}\n')
    entry("surface", "sand", {"material.usda": ("usd", mapped), "surface.json": ("record", "{}")})
    entry("surface", "boards", {"surface.json": ("record", json.dumps({"settings": {"roughness": 0.7}}))})
    entry("surface", "pane", {"surface.json": ("record", json.dumps({"recipe": "glass",
                                                                     "settings": {"roughness": 0.05}}))})
    glass = variant.replace("steel", "glass").replace("(0.3, 0.3, 0.4)", "(0.5, 0.5, 1)\n  float inputs:opacity = 0.2")
    entry("surface", "glass", {"material.usda": ("usd", glass), "surface.json": ("record", "{}")})
    entry("light", "lamp", {"lamps.json": ("record", "{}")})
    screen_glow = piece.GetRootLayer().ExportToString().replace('"box"', '"glow"').replace("</box/", "</glow/")
    entry("model", "monitor", {"model.usda": ("usd", piece.GetRootLayer().ExportToString()),
                               "model_glow.usda": ("usd", screen_glow)})
    entry("model", "slope", {"terrain.usdc": ("usd", None)})
    heights = np.add.outer(np.arange(301) * 0.1, np.zeros(301))  # rising 0.1 m a metre down the rows, 300 m square
    heights[150, 40] = np.nan  # a no-data post
    relief.heightfield_file(relief.filled(heights), 1.0, files / "model/slope@1/terrain.usdc", near=20.0)
    sky = ('#usda 1.0\n(\n defaultPrim = "sky_dome"\n)\ndef Xform "sky_dome"\n{\n def DomeLight "Environment"\n {\n'
           '  float inputs:intensity = 0.2\n }\n}\n')
    entry("light", "sky", {"sky.usda": ("usd", sky)})
    base = piece.GetRootLayer().ExportToString().replace('"box"', '"base"').replace("</box/", "</base/")
    rooted = ('#usda 1.0\n(\n defaultPrim = "crate"\n)\ndef Xform "crate" (\n'
              ' prepend references = @./payloads/base.usda@\n)\n{\n}\n')
    entry("model", "sm_crate", {"simready_usd/payloads/base.usda": ("usd", base),
                                "simready_usd/payloads/sm_crate_01_geo.usda": ("usd", base),
                                "simready_usd/sm_crate_01.usda": ("usd", rooted)})
    for kind, entry_id, written in (("model", "sm_crate", {"usd": {"root": "simready_usd/sm_crate_01.usda"}}),
                                    ("model", "old_crate", {"state": "withdrawn", "replaced_by": "model/old_box@1"}),
                                    ("model", "old_box", {"state": "withdrawn", "replaced_by": "model/sm_crate@1"}),
                                    ("model", "gone", {"state": "withdrawn", "replaced_by": "model/gone_too@1"}),
                                    ("model", "gone_too", {"state": "withdrawn"}),
                                    ("surface", "old_steel", {"state": "withdrawn", "replaced_by": "surface/steel@1"})):
        if kind != "model" or entry_id != "sm_crate":
            entry(kind, entry_id, {})
        path = root / "entries" / kind / entry_id / "1" / "entry.json"
        path.write_text(json.dumps(dict(json.loads(path.read_text()), **written)))


def part_middles(mesh, part):
    """The middles of a mesh's faces in one named part (its GeomSubset), in its own frame."""
    points = np.array(mesh.GetPointsAttr().Get())
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    return np.array([points[indices[starts[face]:starts[face] + counts[face]]].mean(axis=0)
                     for face in subset.GetIndicesAttr().Get()])


def part_solids(mesh, part):
    """The closed solids of one named part (its quads split in two), each a trimesh."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=float)
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    triangles = [[indices[starts[face]], indices[starts[face] + corner], indices[starts[face] + corner + 1]]
                 for face in subset.GetIndicesAttr().Get() for corner in range(1, counts[face] - 1)]
    return trimesh.Trimesh(points, np.array(triangles)).split(only_watertight=True)


def part_facings(mesh, part):
    """Each face of a named part as its middle (x, y, z) and its unit normal by its winding (nx, ny, nz)."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=float)
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    found = []
    for face in subset.GetIndicesAttr().Get():
        corners = points[indices[starts[face]:starts[face] + counts[face]]]
        normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        found.append(np.concatenate([corners.mean(axis=0), normal / np.linalg.norm(normal)]))
    return np.array(found)


def part_bounds(mesh, part):
    """Each face of a named part as its box: (faces, 2, 3), low and high corners."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=float)
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    return np.array([[points[indices[starts[face]:starts[face] + counts[face]]].min(axis=0) - 1e-6,
                      points[indices[starts[face]:starts[face] + counts[face]]].max(axis=0) + 1e-6]
                     for face in subset.GetIndicesAttr().Get()])


def tmp_glb(folder):
    """A glTF of two boxes, one in a material named `door` baked in a red map, one in an unnamed one, the second
    lifted 1 m."""
    door = trimesh.creation.box((1, 1, 1))
    door.visual = trimesh.visual.TextureVisuals(
        uv=np.zeros((len(door.vertices), 2)), material=trimesh.visual.material.PBRMaterial(
            name="door", baseColorTexture=Image.new("RGB", (4, 4), (200, 0, 0))))
    body = trimesh.creation.box((1, 1, 1))
    body.apply_translation((0, 1, 0))
    body.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial())
    return trimesh.Scene([door, body]).export(file_type="glb")


def character():
    """A character asset as tools/characters makes one: its body groups `far` and `made` invisible, a one-joint
    skeleton and its clip `standing` (the joint 1 m up at its start)."""
    body = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(body, UsdGeom.Tokens.y)
    root = UsdSkel.Root.Define(body, "/Character")
    body.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetCustomDataByKey("score:clip_seconds", {"standing": 1.0})
    UsdGeom.Xform.Define(body, "/Character/Turned")
    skeleton = UsdSkel.Skeleton.Define(body, "/Character/Turned/Skeleton")
    skeleton.CreateJointsAttr(["hips"])
    skeleton.CreateRestTransformsAttr([Gf.Matrix4d(1)])
    skeleton.CreateBindTransformsAttr([Gf.Matrix4d(1)])
    for group in ("far", "made"):
        UsdGeom.Xform.Define(body, f"/Character/Turned/Body/{group}").MakeInvisible()
        UsdGeom.Cube.Define(body, f"/Character/Turned/Body/{group}/shape")
    clip = UsdSkel.Animation.Define(body, "/Character/Animations/standing")
    clip.CreateJointsAttr(["hips"])
    clip.CreateTranslationsAttr().Set(Vt.Vec3fArray([(0, 1, 0)]), 0)
    clip.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1)]), 0)
    clip.CreateScalesAttr().Set(Vt.Vec3hArray([Gf.Vec3h(1)]), 0)
    return body.GetRootLayer().ExportToString()


def skinned_asset(path):
    """A skinned character asset as tools/characters/skel_usd.py lays one out, written to `path`: a two-joint
    skeleton (hips 1 m up, chest 0.5 m over it) turned about up in `Turned`, its made body a box skinned from hips to
    chest under a 5 cm geomBindTransform with a blend shape `lean`, its far body hidden, and its clip `standing` of
    a round of two frames (repeated twice, as skel_usd fills its seconds) bending the chest 20 degrees and keying
    `lean` to 0.7 between."""
    body = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(body, UsdGeom.Tokens.y)
    body.SetTimeCodesPerSecond(30)  # skel_usd.RATE, its clips' frames
    root = UsdSkel.Root.Define(body, "/Character")
    body.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetCustomDataByKey("score:clip_seconds", {"standing": 2.0 / 30.0})
    UsdGeom.Xform.Define(body, "/Character/Turned").AddRotateYOp().Set(180.0)
    skeleton = UsdSkel.Skeleton.Define(body, "/Character/Turned/Skeleton")
    skeleton.CreateJointsAttr(["hips", "hips/chest"])
    skeleton.CreateBindTransformsAttr([Gf.Matrix4d().SetTranslate((0, 1, 0)), Gf.Matrix4d().SetTranslate((0, 1.5, 0))])
    skeleton.CreateRestTransformsAttr([Gf.Matrix4d().SetTranslate((0, 1, 0)), Gf.Matrix4d().SetTranslate((0, 0.5, 0))])
    UsdSkel.BindingAPI.Apply(skeleton.GetPrim())
    look = UsdShade.Material.Define(body, "/Character/Looks/coat")
    shader = UsdShade.Shader.Define(body, "/Character/Looks/coat/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.5, 0.2, 0.1))
    look.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    box = trimesh.creation.box((0.4, 0.8, 0.3))
    box.apply_translation((0, 1.2, 0))
    UsdGeom.Scope.Define(body, "/Character/Turned/Body")
    for group in ("made", "far"):
        UsdGeom.Xform.Define(body, f"/Character/Turned/Body/{group}")
        mesh = UsdGeom.Mesh.Define(body, f"/Character/Turned/Body/{group}/box")
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy((box.vertices - (0, 0.05, 0)).astype(np.float32)))
        mesh.CreateFaceVertexCountsAttr([3] * len(box.faces))
        mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(box.faces.ravel().astype(np.int32)))
        binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
        binding.CreateSkeletonRel().SetTargets([skeleton.GetPath()])
        upper = np.clip((box.vertices[:, 1] - 0.8) / 0.8, 0.0, 1.0)
        binding.CreateJointIndicesPrimvar(False, 2).Set(Vt.IntArray([0, 1] * len(box.vertices)))
        binding.CreateJointWeightsPrimvar(False, 2).Set(Vt.FloatArray.FromNumpy(
            np.column_stack([1.0 - upper, upper]).ravel().astype(np.float32)))
        binding.CreateGeomBindTransformAttr(Gf.Matrix4d().SetTranslate((0, 0.05, 0)))
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(look)
        if group == "made":
            shape = UsdSkel.BlendShape.Define(body, f"/Character/Turned/Body/{group}/box/lean")
            top = np.flatnonzero(box.vertices[:, 1] > 1.2)
            shape.CreateOffsetsAttr(Vt.Vec3fArray([Gf.Vec3f(0.1, 0, 0)] * len(top)))
            shape.CreatePointIndicesAttr(Vt.IntArray.FromNumpy(top.astype(np.int32)))
            binding.CreateBlendShapesAttr(["lean"])
            binding.CreateBlendShapeTargetsRel().SetTargets([shape.GetPath()])
        else:
            mesh.MakeInvisible()
    clip = UsdSkel.Animation.Define(body, "/Character/Animations/standing")
    clip.CreateJointsAttr(["hips", "hips/chest"])
    clip.CreateBlendShapesAttr(["lean"])
    for frame, (bend, lean) in enumerate(((0.0, 0.0), (20.0, 0.7), (0.0, 0.0), (20.0, 0.7), (0.0, 0.0))):
        turn = Gf.Quatf(Gf.Rotation(Gf.Vec3d(0, 0, 1), bend).GetQuat())
        clip.CreateTranslationsAttr().Set(Vt.Vec3fArray([(0, 1, 0), (0, 0.5, 0)]), frame)
        clip.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1), turn]), frame)
        clip.CreateScalesAttr().Set(Vt.Vec3hArray([Gf.Vec3h(1), Gf.Vec3h(1)]), frame)
        clip.CreateBlendShapeWeightsAttr().Set(Vt.FloatArray([lean]), frame)
    body.Save()


def cast_skinned(laid, folder):
    """The skinned asset laid as the cast lays characters: `leader` playing its clip while it walks 2 m along x over
    two seconds, and a crowd PointInstancer of two prototypes (the clip from its start and a frame in) at three
    spots."""
    asset = folder / "assets/characters/skinny.usda"
    asset.parent.mkdir(parents=True, exist_ok=True)
    skinned_asset(asset)
    leader = laid.DefinePrim("/yard/Characters/leader", "SkelRoot")
    leader.GetReferences().AddReference("./assets/characters/skinny.usda")
    moves = UsdGeom.Xformable(leader).AddTranslateOp()
    moves.Set(Gf.Vec3d(5, 0, 5), 0)
    moves.Set(Gf.Vec3d(7, 0, 5), 60)
    laid.OverridePrim("/yard/Characters/leader/Turned/Skeleton").CreateRelationship("skel:animationSource").SetTargets(
        [Sdf.Path("/yard/Characters/leader/Animations/standing")])
    crowd = UsdGeom.PointInstancer.Define(laid, "/yard/Characters/crowd")
    prototypes = []
    for phase in (0, 1):
        path = f"/yard/Characters/crowd/Prototypes/standing_{phase}"
        laid.DefinePrim(path, "SkelRoot").GetReferences().AddReference(
            Sdf.Reference("./assets/characters/skinny.usda", layerOffset=Sdf.LayerOffset(-phase)))
        laid.OverridePrim(f"{path}/Turned/Skeleton").CreateRelationship("skel:animationSource").SetTargets(
            [Sdf.Path(f"{path}/Animations/standing")])
        prototypes.append(Sdf.Path(path))
    crowd.CreatePrototypesRel().SetTargets(prototypes)
    crowd.CreatePositionsAttr(Vt.Vec3fArray([(20, 0, 0), (21, 0, 0), (22, 0, 1)]))
    crowd.CreateProtoIndicesAttr(Vt.IntArray([0, 1, 0]))


def tampered(glb, accessor_number):
    """The GLB with one accessor's numbers set to identity matrices (a skin whose inverse binds were never written)."""
    from score.stages.place_build import scene_package
    document, binary = scene_package.unpacked(glb, None)
    found = document["accessors"][accessor_number]
    start = document["bufferViews"][found["bufferView"]]["byteOffset"]
    binary = bytearray(binary)
    binary[start:start + 64 * found["count"]] = np.tile(np.eye(4, dtype=np.float32).ravel(), found["count"]).tobytes()
    return scene_package.packed(document, bytes(binary))


def shown_ground(stage, shown):
    """(the laid ground disc's ground mark, its parts)."""
    return (stage.GetPrimAtPath("/yard/Objects/regolith").GetAttribute("score:ground").Get(),
            next(item for item in shown["objects"] if item["name"] == "regolith")["parts"])


def bound_colour(stage, path):
    look = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(path)).ComputeBoundMaterial()[0]
    return tuple(UsdShade.Shader(stage.GetPrimAtPath(f"{look.GetPath()}/surface")).GetInput("diffuseColor").Get())


def pictures(folder):
    """A concept (blue left half, its object the left half) and a render (blue, its silhouette the left quarter)."""
    concept = np.zeros((40, 80, 3), np.uint8)
    concept[:, :40] = (30, 60, 200)
    Image.fromarray(concept).save(folder / "concept.png")
    Image.fromarray(concept).save(folder / "render.png")
    silhouette = np.zeros((40, 80, 4), np.uint8)
    silhouette[:, :20, 3] = 255
    Image.fromarray(silhouette).save(folder / "render-mask.png")
    object_mask = np.zeros((40, 80), np.uint8)
    object_mask[:, :40] = 255
    Image.fromarray(object_mask).save(folder / "left.png")
    (folder / "objects.json").write_text(json.dumps([{"word": "wall", "box": [0, 0, 40, 40], "score": 0.9,
                                                      "mask": str(folder / "left.png")}]))


def test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them(tmp_path, monkeypatch):
    root, files, folder = tmp_path / "lib", tmp_path / "files", tmp_path / "place"
    library(root, files)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setenv("SCORE_LIB_FILES", str(files))
    Image.new("RGB", (80, 40)).save(tmp_path / "concept.png")
    place_build.start(folder, "yard", tmp_path / "concept.png")
    laid = place_build.put(folder, "wall", "kit/box_piece", at=(1.2, 0.3, -0.8), turn=(0, 80, 0))
    snapped = place_build.snap(folder, "wall", grid=0.5)
    place_build.put(folder, "crate", "kit/box_piece@1", at=(3, 0, 0))
    place_build.surface(folder, "wall", "surface/steel")
    place_build.surface(folder, "crate", "surface/boards", colour="#ff0000")
    place_build.surface(folder, "crate", "surface/steel", part="top")
    place_build.put(folder, "dune", "kit/box_piece", at=(6, 0, 0))
    place_build.surface(folder, "dune", "surface/sand", colour="#ff8000")
    place_build.light(folder, "bulb", at=(0, 2.5, 0), watts=100)
    (tmp_path / "palette.json").write_text(json.dumps({
        "recipes": {"boards": {"roughness": 0.7}, "glass": {"roughness": 0.05}},  # glass before its opacity (#154)
        "tokens": {"hull": "#ff0000", "dust": "#00ff00"}, "dirt": "dust",
        "families": {"paint": {"variants": {"hull_paint": {"recipe": "boards", "token": "hull", "seed": 3}}},
                     "glass": {"variants": {"porthole": {"recipe": "glass", "token": "hull"},
                                            "smoked": {"recipe": "glass", "token": "dust", "opacity": 0.5}}}}}))
    place_build.palette(folder, tmp_path / "palette.json", wear=0.4, dirt=0.3)
    place_build.put(folder, "screen", "model/monitor", at=(12, 0, 0))
    place_build.surface(folder, "screen", "palette/hull_paint", part="glow")
    place_build.put(folder, "panel", "kit/box_piece", at=(14, 0, 0))
    place_build.surface(folder, "panel", "surface/pane", colour="#ffffff")  # a recipe's glass, before its opacity
    paned = Sdf.Layer.FindOrOpen(str(folder / "scene.usda"))
    pane_opacity = paned.GetAttributeAtPath("/yard/Looks/panel/surface.inputs:opacity").default
    del paned  # a layer held open is read again stale by the steps after
    place_build.surface(folder, "panel", "palette/hull_paint")
    batched = place_build.batch(folder, [
        {"step": "put", "name": "floor", "address": "kit/box_piece", "at": [0, -2, 0], "scale": 4, "ground": True},
        {"step": "put", "name": "missing", "address": "kit/plan_only"},
        {"step": "put", "name": "cabinet", "address": "model/cabinet"},
        {"step": "put", "name": "walker", "address": "character/walker", "at": [2, 0, 2]},
        {"step": "dome", "name": "dome", "radius": 5.0, "meridians": 8, "rings": 2, "rib": 0.1},
        {"step": "dome", "name": "holed", "radius": 5.0, "at": [40, 0, 0], "openings": [[0, 1.2, 1.0]],
         "base": [0.4, 0.3], "oculus": 0.8, "strips": [2.0]},
        {"step": "tube", "name": "hall", "radius": 1.5, "length": 3.0, "at": [60, 0, 0], "cap": [1.6, 2.0],
         "trims": [[0, 0, -3.0, 4.0]]},
        {"step": "ground", "name": "regolith", "radius": 3.0},
        {"step": "put", "name": "cup", "address": "take/cup"},
        {"step": "tube", "name": "tunnel", "radius": 1.5, "length": 4.0, "at": [20, 0, 0], "hoops": 3},
        {"step": "put", "name": "shelf", "address": "model/cabinet", "at": [9, 0.75, 0], "rest": True},
        {"step": "stairs", "name": "stairwell", "storeys": 1, "mirror": True}])
    refusals = []
    for step in (lambda: place_build.put(folder, "plan", "kit/plan_only"),
                 lambda: place_build.surface(folder, "wall", "surface/boards")):
        try:
            step()
        except place_build.Refused as why:
            refusals.append(str(why))
    smoked = place_build.batch(folder, [
        {"step": "put", "name": "wisp", "address": "effect/wisp", "at": [2, 1.2, 2]},
        {"step": "put", "name": "stub", "address": "kit/box_piece", "at": [30, 0, 30]},
        {"step": "hold", "name": "walker", "address": "character/hold", "prop": "stub"}])
    place_build.terrain(folder, "plain", "model/slope", at=(0, 0, 0), turn=(0, 90, 0), pads=[(30.0, 0.0, 5.0)])
    place_build.sky(folder, "light/sky", elevation=30, heading=0, turn=30, exposure=0.7)
    place_build.view(folder, "inside", eye=(0, 1.6, 0), aim=(1, 1.6, 0), fov=70)
    stone = place_build.put(folder, "stone", "model/cabinet", at=(80, -0.1, 0), rest=True, on_ground=True)
    reads = []

    class Reads(dict):
        def __setitem__(self, key, value):
            reads.append(key)
            super().__setitem__(key, value)
    monkeypatch.setattr(place_build, "GROUND_POINTS", Reads())
    pebbles = place_build.batch(folder, [{"step": "put", "name": f"pebble{number}", "address": "model/cabinet",
                                          "at": [70, 0, number], "on_ground": True} for number in range(3)])
    assert len(reads) == 1 and all("refused" not in pebble for pebble in pebbles), pebbles  # one ground read
    for number in range(3):
        place_build.remove(folder, f"pebble{number}")
    place_build.put(folder, "gone", "kit/box_piece")
    place_build.remove(folder, "gone")
    shown = place_build.listing(folder)
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    boxes = {item["name"]: item["box"] for item in shown["objects"]}
    pictures(folder)
    compared = measure.compare(folder)
    assert (laid["usd"], snapped["at"], snapped["turn"]) == ("./assets/kit/box_piece/1/piece.usda", [1.0, 0.3, -1.0],
                                                             [0.0, 90.0, 0.0])
    assert (UsdGeom.GetStageUpAxis(stage), UsdGeom.GetStageMetersPerUnit(stage)) == ("Y", 1.0)
    assert np.allclose(boxes["wall"], [[1.0, 0.3, -2.0], [1.5, 2.3, -1.0]], atol=1e-3)
    assert np.allclose(boxes["crate"], [[3.0, 0.0, 0.0], [4.0, 2.0, 0.5]], atol=1e-3)
    assert np.allclose(bound_colour(stage, "/yard/Objects/wall/geo"), (0.3, 0.3, 0.4))
    assert np.allclose(bound_colour(stage, "/yard/Objects/crate/geo"), (1.0, 0.0, 0.0))
    assert np.allclose(bound_colour(stage, "/yard/Objects/crate/lid/top"), (0.3, 0.3, 0.4))
    assert np.allclose(bound_colour(stage, "/yard/Objects/crate/lid/rim"), (1.0, 0.0, 0.0))
    tint = UsdShade.Shader(stage.GetPrimAtPath("/yard/Looks/dune/colour")).GetInput("scale").Get()
    assert np.allclose(tint, (1.0, 0.2158605, 0.0, 1.0), atol=1e-5)
    assert ["no USD file" in answer.get("refused", "") for answer in batched] == [False, True] + [False] * 10
    door_look = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath("/yard/Objects/cabinet/geo/door")).ComputeBoundMaterial()[0]
    door_map = UsdShade.Shader(stage.GetPrimAtPath(f"{door_look.GetPath()}/base")).GetInput("file").Get()
    assert np.allclose(Image.open(door_map.resolvedPath).getpixel((0, 0)), (200, 0, 0))
    assert UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/yard/Objects/cabinet/geo")).GetPrimvar("st").HasValue()
    assert batched[8]["usd"].endswith("cup-final.usdc") and shown_ground(stage, shown) == (True, {"ground": None})
    assert stage.GetPrimAtPath("/yard/Objects/floor").GetAttribute("score:ground").Get() is True
    cabinet_parts = sorted(next(item for item in shown["objects"] if item["name"] == "cabinet")["parts"])
    assert cabinet_parts[0] == "door" and cabinet_parts[1].startswith("part_") and len(cabinet_parts) == 2
    assert np.allclose(boxes["cabinet"], [[-0.5, -0.5, -0.5], [0.5, 1.5, 0.5]], atol=1e-3)
    assert np.allclose(boxes["shelf"], [[8.5, 0.75, -0.5], [9.5, 2.75, 0.5]], atol=1e-3)
    walker = stage.GetPrimAtPath("/yard/Objects/walker")
    shown_groups = {group: UsdGeom.Imageable(stage.GetPrimAtPath(f"/yard/Objects/walker/Turned/Body/{group}"))
                    .ComputeVisibility() for group in ("far", "made")}
    held = UsdSkel.Animation(stage.GetPrimAtPath("/yard/Objects/walker/Held"))
    wisp = stage.GetPrimAtPath("/yard/Effects/wisp")
    assert (smoked[0]["usd"], wisp.GetAttribute("score:role").Get()) == ("./assets/effect/wisp/1/effect.usda", "effect")
    assert wisp.GetAttribute("score:effect:kind").Get() == "smoke_wisp" and "refused" not in smoked[2], smoked
    assert held.GetPrim().GetAttribute("score:pose").Get() == "character/hold@1"
    turn = held.GetRotationsAttr().Get()[0]
    assert np.allclose([turn.GetReal(), *turn.GetImaginary()], [0.7071068, 0.0, 0.7071068, 0.0], atol=1e-6)
    stub = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Objects/stub")).ComputeLocalToWorldTransform(0)
    assert np.allclose(stub.ExtractTranslation(), (2.0, 1.0, 1.9), atol=1e-5)  # the hips' +x turned onto -z
    assert np.allclose(stub.TransformDir(Gf.Vec3d(1, 0, 0)), (0.0, 0.0, -1.0), atol=1e-5)
    assert np.allclose(stub.TransformDir(Gf.Vec3d(0, 1, 0)), (1.0, 0.0, 0.0), atol=1e-5)  # held about x, then the hips
    assert (walker.GetTypeName(), shown_groups) == ("SkelRoot", {"far": "invisible", "made": "inherited"})
    assert list(held.GetTranslationsAttr().Get()) == [Gf.Vec3f(0, 1, 0)] and batched[3]["clip"] == "standing"
    spec = json.loads(stage.GetPrimAtPath("/yard/Looks/panel").GetAttribute("score:recipe:spec").Get())
    assert (spec["recipe"], spec["wear"], spec["dirt"], spec["dirt_colour"], spec["hex"]) == ("boards", 0.4, 0.3,
                                                                                               [0.0, 1.0, 0.0], "#ff0000")
    assert stage.GetPrimAtPath("/yard/Objects/panel").GetAttribute("score:surface").Get() == "surface/boards@1"
    method = json.loads((place_build.REPO / "data/library/materials.json").read_text())["recipes"]["glass"]
    assert place_build.palette_spec(folder, "porthole")["opacity"] == method["opacity"] < 1.0  # see-through
    assert np.isclose(pane_opacity, method["opacity"]), pane_opacity  # the method's, as palette_spec takes it
    assert np.allclose(bound_colour(stage, "/yard/Objects/screen/glow/geo"), (1.0, 0.0, 0.0))
    assert np.allclose(bound_colour(stage, "/yard/Objects/screen/geo"), (0.0, 1.0, 0.0))
    holed = UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/holed/geo"))
    shell_middles = part_middles(holed, "shell")
    in_hole = (shell_middles[:, 0] > 0) & (np.hypot(shell_middles[:, 1] - 1.0, shell_middles[:, 2]) < 1.2)
    base_middles = part_middles(holed, "base")
    assert not in_hole.any() and len(shell_middles) > 1000
    assert not ((base_middles[:, 0] > 4.0) & (np.abs(base_middles[:, 2]) < 0.5)).any() and len(base_middles)
    strip_middles, rib_middles = part_middles(holed, "strip"), part_middles(holed, "ribs")
    assert np.allclose(base_middles[:, 1].max(), 0.4, atol=0.01) and len(strip_middles)
    assert np.abs(strip_middles[:, 1] - 2.0).max() < 0.1 and np.linalg.norm(strip_middles, axis=1).max() < 5.0 - 0.05
    assert np.hypot(rib_middles[:, 0], rib_middles[:, 2]).min() > 0.6  # the meridians end at the oculus ring
    solids = part_solids(holed, "base") + part_solids(holed, "ribs")
    assert len(solids) >= 4 and all(solid.volume > 0 for solid in solids)  # faces out: an engine draws fronts only
    hall = UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/hall/geo"))
    cap_middles, hall_skin = part_middles(hall, "cap"), np.vstack([part_middles(hall, "shell"), part_middles(hall, "wall")])
    doorway = (np.abs(cap_middles[:, 0]) < 0.75) & (cap_middles[:, 1] > 0.5) & (cap_middles[:, 1] < 2.4)
    assert len(cap_middles) and not doorway.any() and np.allclose(cap_middles[:, 2].max(), 3.0, atol=0.01)
    cap_points = np.array(hall.GetPointsAttr().Get())[np.array(hall.GetFaceVertexIndicesAttr().Get()).reshape(-1, 4)[
        np.array(next(item for item in UsdGeom.Subset.GetAllGeomSubsets(hall) if item.GetPrim().GetName() == "cap")
                 .GetIndicesAttr().Get())]].reshape(-1, 3)
    off_axis = np.hypot(cap_points[:, 0], cap_points[:, 1] - 1.5)
    assert off_axis.max() <= 1.5 + 1e-5 and np.count_nonzero(off_axis > 1.5 - 1e-5) > 50
    assert np.linalg.norm(hall_skin - [0.0, 0.0, -3.0], axis=1).min() >= 4.0 - 1e-3 and hall_skin[:, 2].min() < 0.5
    hall_points = np.array(hall.GetPointsAttr().Get())
    on_glass = np.abs(np.linalg.norm(hall_points - [0.0, 0.0, -3.0], axis=1) - 4.0) < 1e-3
    assert np.count_nonzero(on_glass) >= 40  # its end runs along the dome's glass, never in steps
    assert part_middles(hall, "wall")[:, 1].max() < 0.45 + 0.8 < part_middles(hall, "shell")[:, 1].min()
    assert sorted(next(item for item in shown["objects"] if item["name"] == "dome")["parts"]) == ["base", "deck", "ribs", "shell"]
    assert sorted(next(item for item in shown["objects"] if item["name"] == "tunnel")["parts"]) == ["deck", "ribs", "shell", "wall"]
    assert np.allclose(boxes["tunnel"], [[18.38, -0.12, 0.0], [21.62, 3.12, 4.0]], atol=0.01)
    assert np.allclose(boxes["dome"], [[-5.18, 0.0, -5.18], [5.18, 5.1, 5.18]], atol=0.02)  # its plinth
    assert shown["lights"] == [{"name": "bulb", "at": [0.0, 2.5, 0.0], "watts": 100.0},
                              {"name": "sun", "at": [0, 0, 0], "watts": 1.0}]
    assert "no USD file" in refusals[0] and "give --colour" in refusals[1] and len(refusals) == 2
    assert set(boxes) == {"wall", "crate", "floor", "cabinet", "walker", "dome", "regolith", "cup", "plain", "sky", "shelf", "tunnel", "stone", "dune", "screen", "holed", "hall", "panel", "stairwell", "stub"} and not stage.GetPrimAtPath("/yard/Objects/gone")
    laid_terrain = stage.GetPrimAtPath("/yard/Objects/plain")
    ground_points = np.array(UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/plain/geo")).GetPointsAttr().Get())
    in_pad = np.hypot(ground_points[:, 0], ground_points[:, 2] - 30.0) < 5.0  # the terrain's own frame
    far = np.abs(ground_points[:, 2]) > 100.0
    posts = np.diff(np.unique(ground_points[:, 0]))
    assert laid_terrain.GetAttribute("score:ground").Get() and np.isfinite(ground_points).all()
    assert np.allclose(ground_points[in_pad, 1], 0.0) and np.ptp(ground_points[far, 1]) > 20.0
    assert posts.max() > 2.0 and np.isclose(posts.min(), 1.0)
    assert np.isclose(stone["at"][1], 0.5 + 8.0 - 0.1, atol=0.001)  # 80 m along the turned slope: 8 m up, on its face
    sun = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Lights/sun")).ComputeLocalToWorldTransform(0)
    shines = sun.TransformDir(Gf.Vec3d(0, 0, -1))
    assert stage.GetPrimAtPath("/yard/Environment").GetAttribute("inputs:intensity").Get() == np.float32(0.2)
    assert stage.GetPrimAtPath("/yard/Environment").GetAttribute("score:exposure").Get() == np.float32(0.7)
    assert np.allclose(shines, (-np.cos(np.radians(30)), -0.5, 0.0), atol=1e-6)
    assert place_build.pose_of(stage.GetPrimAtPath("/yard/Objects/sky"))[1] == [0.0, 30.0, 0.0]
    final = render.views(place_build.record_of(folder), 80, [], final=True)
    assert final["review"] is False and final["size"] == [1920, 1080]
    monkeypatch.delenv("SCORE_BLENDER_LIBS", raising=False)
    linked = render.BLENDER.parent.parent / "libs"
    assert f"--setenv=LD_LIBRARY_PATH={linked}:/usr/lib/wsl/lib" in render.queued("job", "script.py", [], card=False) \
        and "tools/blender/setup.sh" in render.unlinked_hint(127) and render.unlinked_hint(1) == ""
    core = UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/stairwell/geo"))
    treads, walls = part_facings(core, "steps"), part_bounds(core, "wall")
    up = treads[np.abs(treads[:, 4]) > 0.99]
    rises = np.diff(np.unique(np.round(up[up[:, 4] > 0, 1], 3)))
    door = batched[11]["doorways"][1]  # the first floor's flat door, in the back wall
    middle = (stair_core.LONG - (door[1] + door[2]) / 2, (door[3] + door[4]) / 2, stair_core.DEEP + stair_core.WALL / 2)
    in_door = np.all((walls[:, 0, :2] <= middle[:2]) & (walls[:, 1, :2] >= middle[:2]), axis=1) \
        & (np.abs(walls[:, 0, 2] - middle[2]) <= stair_core.WALL / 2 + 1e-3)  # a wall face across the doorway
    assert len(up) and (up[:, 4] > 0).all() and rises.max() <= 0.3 and not in_door.any()
    curtain = stair_core.front_windows(2, curtain=True)  # a storey-high glazed front, clear of the slab over each
    assert len(curtain) == 3 and all(x1 - x0 > stair_core.LONG - 0.5 and head - sill > 2.4
                                     and head <= (sill // stair_core.STOREY + 1) * stair_core.STOREY - stair_core.SLAB
                                     for x0, x1, sill, head in curtain)
    stair_core.core(tmp_path / "cut.usda", 1, cut=True, one_block=True)
    cut_stage = Usd.Stage.Open(str(tmp_path / "cut.usda"))
    cut = np.asarray(UsdGeom.Mesh(cut_stage.GetPrimAtPath("/stair_core/geo")).GetPointsAttr().Get())
    in_front = (cut[:, 0] > 0) & (cut[:, 0] < stair_core.LONG) & (cut[:, 2] < 0) & (cut[:, 1] > 0.5)
    assert not in_front.any(), cut[in_front][:3]  # the cut-away holds no front wall over its open front
    standing = cut[cut[:, 1] > 0.5]  # one block: nothing stands past the shaft's far wall, the entrance's block kept
    assert standing[:, 0].max() <= stair_core.LONG + stair_core.WALL + 1e-6 and standing[:, 0].min() < -stair_core.BLOCK
    corner = np.isclose(cut, (0.0, 0.0, -stair_core.FACADE), atol=1e-6).all(axis=1)  # the pier's foot at the facade
    cut_mesh = UsdGeom.Mesh(cut_stage.GetPrimAtPath("/stair_core/geo"))
    flat = np.asarray(cut_mesh.GetNormalsAttr().Get())
    assert corner.any() and cut_mesh.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying \
        and len(flat) == sum(cut_mesh.GetFaceVertexCountsAttr().Get()) and np.allclose(np.linalg.norm(flat, axis=1), 1.0)
    stair_core.core(tmp_path / "street.usda", 1, mirror=True, one_block=True, street=True)  # a lobby's street door
    street_stage = Usd.Stage.Open(str(tmp_path / "street.usda"))
    lobby = UsdGeom.Mesh(street_stage.GetPrimAtPath("/stair_core/geo"))
    spots = stair_core.doorway_spots(1, mirror=True, street=True)
    street_door = np.array(spots["street"]["middle"]) + [0.0, 1.0, 0.0]
    across = part_bounds(lobby, "block")
    walled = np.all((across[:, 0, :2] <= street_door[:2]) & (across[:, 1, :2] >= street_door[:2]), axis=1) \
        & (np.abs(across[:, 0, 2] - street_door[2]) <= stair_core.WALL / 2 + 1e-3)  # a facade face across it
    pane = np.abs(part_middles(lobby, "glass")[:, 0] - street_door[0]) < stair_core.DOOR[0] / 2
    assert not walled.any() and not (pane & (part_middles(lobby, "glass")[:, 1] < stair_core.STOREY)).any() \
        and spots["street"]["inward"] == [-0.0, 0.0, 1.0] and np.isclose(spots["street"]["wide"], stair_core.DOOR[0]) \
        and street_door[0] > stair_core.LONG + stair_core.WALL and "street" not in stair_core.doorway_spots(1)
    place_build.start(tmp_path / "well", "well", tmp_path / "concept.png")  # a cut core laid again in one batch
    relaid = place_build.batch(tmp_path / "well", [{"step": "stairs", "name": "core", "storeys": 1, "cut": True},
                                                   {"step": "stairs", "name": "core", "storeys": 1, "cut": True,
                                                    "street": True}])
    assert relaid[1]["street"] and "core_street" in place_build.record_of(tmp_path / "well")["doorways"], relaid
    stair_core.front_alone(tmp_path / "front.usda", 1)  # the wall a cut core leaves to its own object
    front_stage = Usd.Stage.Open(str(tmp_path / "front.usda"))
    front = np.asarray(UsdGeom.Mesh(front_stage.GetPrimAtPath("/stair_front/geo")).GetPointsAttr().Get())
    assert ((front[:, 0] > 0) & (front[:, 0] < stair_core.LONG) & (front[:, 2] < 0) & (front[:, 1] > 0.5)).any()
    listed_views = render.views(place_build.record_of(folder), 80, ["inside"])["views"]
    assert [view["name"] for view in listed_views] == ["concept", "inside"] and listed_views[1]["look_only"]
    assert (compared["layout_iou"], compared["objects"][0]["covered"], compared["colour"]["mean"]) == (0.5, 0.5, 0.0)
    assert measure.lab(Image.open(folder / "concept.png").convert("RGB"))[0, 0, 2] < -40
    assert Image.open(compared["picture"]).size == (3 * measure.PANEL, measure.PANEL // 2)
    built = place_build.blocks(folder, "kerb", [[0, 0, 0, 2, 0.15, 0.3, "kerb"], [0, 0, 0.3, 2, 0.004, 0.5, "line"]],
                               at=(50, 0, 50))
    place_build.blocks(folder, "road", [[0, -0.3, 0, 4, 0, 4, "road"]], at=(60, 0, 60), ground=True)
    place_build.put(folder, "sill", "kit/box_piece", at=(50, 1, 52), role="mount", support="wall:kerb")
    place_build.night(folder, [0.01, 0.04, 0.08], [0.01, 0.04, 0.08], 2.5,
                      {"elevation": 30, "heading": 90, "strength": 0.01, "colour": [0.5, 0.7, 1.0]})
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    kerb = trimesh.Trimesh(*[np.array(value) for value in (
        UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/kerb/geo")).GetPointsAttr().Get(),
        np.array(UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/kerb/geo")).GetFaceVertexIndicesAttr().Get()
                 ).reshape(-1, 3))]).split(only_watertight=False)
    marks = {name: [stage.GetPrimAtPath(f"/yard/Objects/{name}").GetAttribute(f"score:{key}").Get()
                    for key in ("role", "support", "ground")] for name in ("kerb", "road", "sill")}
    moon = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Lights/moon")).ComputeLocalToWorldTransform(0)
    assert built["boxes"] == 2 and len(kerb) == 2 and all(piece.is_watertight and piece.volume > 0 for piece in kerb)
    assert sorted(subset.GetPrim().GetName() for subset in UsdGeom.Subset.GetAllGeomSubsets(
        UsdGeom.Imageable(stage.GetPrimAtPath("/yard/Objects/kerb/geo")))) == ["kerb", "line"]
    assert marks == {"kerb": ["structure", None, False], "road": [None, None, True], "sill": ["mount", "wall:kerb", False]}
    assert stage.GetPrimAtPath("/yard/Environment").GetAttribute("score:exposure").Get() == np.float32(2.5)
    assert np.allclose(moon.TransformDir(Gf.Vec3d(0, 0, -1)), (0.0, -0.5, -np.cos(np.radians(30))), atol=1e-6)
    rained(folder)
    reviewed(folder)
    packaged(folder, tmp_path / "package")
    drafted(folder, tmp_path / "draft")
    pieced(folder, root, tmp_path / "pieces")
    resumed(tmp_path / "resumed")
    side_by_side(tmp_path / "side")
    sized_and_timed(tmp_path / "sized")
    filmed(tmp_path)
    doored(tmp_path)
    stilled(folder)
    from_library(tmp_path, root, files)
    skied(tmp_path, root, files)
    adopted(tmp_path / "adopted")
    replaced(tmp_path)


def adopted(folder):
    """An adopted asset (#155) as the package reads it: its prop's mass the one its asset authors (UsdPhysics' MassAPI
    on its mesh) times its scale cubed, over its entry's record; its look's UsdPreviewSurface as Blender's importer
    reads it, the ORM map's green its roughness and blue its metal (red, occlusion, unread, as Blender reads none),
    the normal map (scale 2, bias -1) as glTF holds one, unchanged."""
    from score.stages.place_build import scene_package
    record = folder / "assets/model/adopted/1/adopted.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"physics": {"mass_kg": 3.0}}))
    stage = Usd.Stage.CreateInMemory()
    prop = stage.DefinePrim("/p/Objects/prop_1", "Xform")
    prop.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set("model/adopted@1")
    geo = UsdGeom.Mesh.Define(stage, "/p/Objects/prop_1/geo").GetPrim()
    UsdPhysics.MassAPI.Apply(geo).CreateMassAttr(1.5496)
    assert scene_package.mass_of(folder, prop, 2.0) == round(1.5496 * 8, 4)
    assert scene_package.collider_of(folder, prop, "prop", 2.0)["mass_kg"] == round(1.5496 * 8, 4)
    maps = {"alb": (200, 100, 50), "orm": (30, 140, 220), "nor": (128, 120, 250)}
    for name, colour in maps.items():
        Image.new("RGB", (8, 8), colour).save(folder / f"{name}.png")
    look = UsdShade.Material.Define(stage, "/p/Looks/painted")
    shader = UsdShade.Shader.Define(stage, "/p/Looks/painted/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    look.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    for name, wiring in (("alb", [("rgb", "diffuseColor", Sdf.ValueTypeNames.Color3f)]),
                         ("orm", [("g", "roughness", Sdf.ValueTypeNames.Float),
                                  ("b", "metallic", Sdf.ValueTypeNames.Float)]),
                         ("nor", [("rgb", "normal", Sdf.ValueTypeNames.Normal3f)])):
        texture = UsdShade.Shader.Define(stage, f"/p/Looks/painted/{name}")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(str(folder / f"{name}.png"))
        if name == "nor":
            texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2, 2, 2, 1))
            texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 0))
        for output, wired, kind in wiring:
            shader.CreateInput(wired, kind).ConnectToSource(texture.ConnectableAPI(), output)
    material = scene_package.pbr(look)["material"]
    assert material.metallicRoughnessTexture.getpixel((0, 0))[1:] == (140, 220)
    assert material.metallicFactor == material.roughnessFactor == 1.0
    assert material.normalTexture.getpixel((0, 0)) == maps["nor"]
    assert material.baseColorTexture.getpixel((0, 0)) == maps["alb"]


def replaced(tmp_path):
    """A withdrawn model and surface that name their replacements laid as the end of the chain (#155): the retired
    crate, through a retired box, as the adopted crate laid by its record's usd root (its payloads beside it, one named
    like the root's layers, never laid as a layer), the retired steel as the steel; a chain ending withdrawn refused."""
    folder = tmp_path / "replaced"
    Image.new("RGB", (8, 8)).save(tmp_path / "replaced.png")
    place_build.start(folder, "depot", tmp_path / "replaced.png")
    laid = place_build.put(folder, "crate", "model/old_crate")
    worn = place_build.surface(folder, "crate", "surface/old_steel@1")
    assert (laid["address"], laid["usd"], laid.get("layers")) == (
        "model/sm_crate@1", "./assets/model/sm_crate/1/simready_usd/sm_crate_01.usda", None), laid
    assert worn["surface"] == "surface/steel@1", worn
    stage, _ = place_build.opened(folder)
    assert stage.GetPrimAtPath("/depot/Objects/crate/geo"), "the adopted crate's root references its base payload"
    with pytest.raises(place_build.Refused, match="gone_too@1: withdrawn"):
        place_build.put(folder, "lost", "model/gone")


def skied(tmp_path, root, files):
    """A Moon place's physical sky from its site and time: what overhead.py says is overhead (the light stage's
    gate, sky.faults, on the turned answer), Earth in its library face, Mars's withdrawn face named missing, the sky
    laid before cleared, black at the Sun's exposure; a Mars site refused for its air."""
    from score.review import overhead, setting as settings
    from score.stages.light import sky
    face = {"body": "earth", "surface": "earth_face", "family": "ocean", "recipe": "ocean", "token": "sea",
            "colour": [0.1, 0.2, 0.5], "roughness": 0.4, "metal": 0.0}
    for body, state in (("earth", "active"), ("mars", "withdrawn")):
        folder = root / "entries/surface" / f"{body}_face" / "1"
        folder.mkdir(parents=True)
        folder.joinpath("entry.json").write_text(json.dumps({
            "schema": "score-lib-entry/1", "address": f"surface/{body}_face@1", "kind": "surface",
            "id": f"{body}_face", "version": 1, "state": state, "files": {"face.json": {"role": "record"}}}))
        target = files / f"surface/{body}_face@1/face.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({**face, "body": body, "surface": f"{body}_face"}))
    Image.new("RGB", (8, 8)).save(tmp_path / "moon.png")
    folder = tmp_path / "moon_place"
    place_build.start(folder, "lock", tmp_path / "moon.png")
    place_build.sky(folder, "light/sky", elevation=30, heading=0)
    site = {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}
    when = "2099-10-01T14:00:00Z"
    laid = place_build.sky_at(folder, on="moon", latitude=55.0, longitude=0.0, time=when, turn=40.0)
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    seen = place_build.turned(overhead.seen(settings.now(), site, when), 40.0)
    environment = stage.GetPrimAtPath("/lock/Environment")
    sun = overhead.risen(seen)["lights"][0]
    assert sky.faults(seen, sky.held(stage, "lock")) == [] and laid["lights"] == ["Sun"], laid
    assert not stage.GetPrimAtPath("/lock/Lights/sun") and not stage.GetPrimAtPath("/lock/Objects/sky")
    assert np.allclose(bound_colour(stage, "/lock/Sky/Bodies/earth"), (0.1, 0.2, 0.5))
    assert stage.GetPrimAtPath("/lock/Sky/Bodies/earth").GetAttribute("score:library").Get() == "surface/earth_face@1"
    assert "withdrawn" in laid["faces missing"]["mars"] and \
        "withdrawn" in stage.GetPrimAtPath("/lock/Sky/Bodies/mars").GetAttribute("score:surface:missing").Get()
    assert tuple(environment.GetAttribute("score:background").Get()) == (0.0, 0.0, 0.0)
    assert np.isclose(environment.GetAttribute("score:exposure").Get(), np.pi * sky.LUMENS_PER_WATT / sun["lux"])
    from score.stages.place_build import scene_package
    assert scene_package.environment_of(stage, "lock", tmp_path / "moon_package")["sun"] is not None  # the game's sun
    built = [prim for prim in (stage.GetPrimAtPath("/lock/Lights/sky_sun"), stage.GetPrimAtPath("/lock/Environment"),
                               stage.GetPrimAtPath("/lock/Sky/Discs/sun"))]
    assert all(str(prim.GetAttribute("score:from").Get()).endswith(place_build.SKY_ALGORITHM) for prim in built), built
    assert stage.GetPrimAtPath("/lock/Looks/sun_disc").GetAttribute("score:surface").Get() == place_build.GLOWING
    try:
        place_build.sky_at(folder, on="mars", latitude=30.0, longitude=130.0, time=when)
        raise AssertionError("a Mars site was laid under an airless sky")
    except place_build.Refused as why:
        assert "has air" in str(why)


def from_library(tmp_path, root, files):
    """A place entry laid out as a place_build folder (`place_build from`): each file at its own name, the scene
    opening as a placed folder, its sublayer the entry does not hold (the films' walkers layer) dropped and named; a
    folder not empty refused."""
    entry_folder = root / "entries/place/lane/1"
    entry_folder.mkdir(parents=True)
    names = {"scene.usda": "usd", "place.json": "record", "assets/model/kerb.usda": "usd"}
    entry_folder.joinpath("entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": "place/lane@1", "kind": "place", "id": "lane", "version": 1,
        "files": {name: {"role": role} for name, role in names.items()}, "provenance": {}}))
    held = files / "place/lane@1"
    (held / "assets/model").mkdir(parents=True)
    (held / "scene.usda").write_text('#usda 1.0\n(\n    defaultPrim = "lane"\n    subLayers = [@layers/walkers/'
                                     'people.usda@]\n)\ndef Xform "lane" {\n    def "box" (\n        prepend '
                                     'references = @score_lib/kit/box_piece/1/piece.usda@\n    ) {}\n}\n')
    (held / "place.json").write_text(json.dumps({"place": "lane"}))
    (held / "assets/model/kerb.usda").write_text('#usda 1.0\ndef "kerb" (\n    prepend references = '
                                                 '@score_lib/kit/box_piece/1/piece.usda@\n) {}\n')
    laid = place_build.from_library("place/lane", tmp_path / "fetched")
    stage, place = place_build.opened(tmp_path / "fetched")
    assert laid == {"address": "place/lane@1", "files": 3, "dropped": ["layers/walkers/people.usda"],
                    "entries": ["kit/box_piece@1"]}, laid
    assert place == "lane" and list(stage.GetRootLayer().subLayerPaths) == [] and \
        (tmp_path / "fetched/assets/model/kerb.usda").is_file()
    kerb = Sdf.Layer.FindOrOpen(str(tmp_path / "fetched/assets/model/kerb.usda"))
    assert stage.GetPrimAtPath("/lane/box").IsValid() and stage.GetPrimAtPath("/lane/box").GetChildren() and \
        (tmp_path / "fetched/assets/kit/box_piece/1/piece.json").is_file() and \
        kerb.GetCompositionAssetDependencies() == ["../kit/box_piece/1/piece.usda"]  # on no search path
    try:
        place_build.from_library("place/lane", tmp_path / "fetched")
        raise AssertionError("a place was laid out over a folder that is not empty")
    except place_build.Refused:
        pass


def rained(folder):
    """The rain falls through its box from its top to the ground and back along its streaks' lean, laid as an effect,
    and a frame shows a splash where, and only where, a drop has reached the ground on it or the frames before, on the
    surface under it (the place's highest solid there, `surface_under`, not y 0: the yard's terrain stands over it); the
    tracks' ruts and prints stand over the laid ground, the ruts between their berms."""
    from score.stages.place_build import ground_tracks, rainfall, ready
    laid = place_build.rain(folder, "rain", [60.0, 60.0], [64.0, 64.0], 3.0, 2.0, seed=1)
    floor = place_build.surface_under(ready.solids(folder), 3.0)  # the ground the rain was laid on, before the ruts
    tracked = place_build.tracks(folder, "ruts", rover=[[[60.5, 62.0], [63.5, 62.0]]],
                                 boots=[[[61.0, 61.0], [63.0, 61.0]]])
    place_build.surface(folder, "ruts", "surface/sand", colour="#8e4a2e")
    place_build.haze(folder, "mist", [62.0, 1.0, 62.0], [4.0, 2.0, 4.0], "#c8c8d0", 0.05)
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    hazed = [prim for prim in Usd.PrimRange(stage.GetPrimAtPath("/yard/Haze/mist")) if prim.HasAttribute("score:from")]
    assert hazed and all(prim.GetAttribute("score:from").Get().endswith(place_build.HAZE_ALGORITHM) for prim in hazed) \
        and any(prim.IsA(UsdShade.Material) for prim in hazed), [str(prim.GetPath()) for prim in hazed]
    effect = stage.GetPrimAtPath("/yard/Effects/rain")
    fall = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Effects/rain/Fall"))
    period = rainfall.period_frames(3.0)
    slid = [np.array(fall.ComputeLocalToWorldTransform(code).ExtractTranslation()) for code in (0.0, period - 0.02,
                                                                                                period)]
    streaks = np.asarray(UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Effects/rain/Fall/streaks")).GetPointsAttr().Get())
    cards = streaks.reshape(-1, 4, 3)[:len(streaks) // 8]
    feet, along = (cards[:, 0] + cards[:, 1]) / 2.0, cards[0, 2] - cards[0, 1]
    assert np.allclose(np.cross(along, slid[1]), 0.0, atol=1e-3 * np.linalg.norm(slid[1]))
    holders = [UsdGeom.Xformable(prim) for prim in stage.GetPrimAtPath("/yard/Effects/rain/Splashes").GetChildren()]
    under_feet = np.zeros(len(feet))
    for _ in range(3):  # each drop's own ground, at the spot its foot reaches it along its lean
        down = feet[:, 1] - under_feet
        under_feet = np.nan_to_num(floor(feet[:, 0] - rainfall.LEAN * down, feet[:, 2] - rainfall.LEAN * 0.3 * down),
                                   nan=0.0)
    def fallen(frame):
        """The streaks' feet at the frame before `frame` and where they are at `frame` itself had they not jumped."""
        start, late = (np.array(fall.ComputeLocalToWorldTransform(code).ExtractTranslation()) for code in
                       (frame - 1.0, frame - 0.01))
        return feet + start, feet + start + (late - start) / 0.99

    for frame in range(len(rainfall.SPLASH_GROWTH), 2 * period + 1):
        before, now = fallen(frame)
        landed = []
        for back in range(len(rainfall.SPLASH_GROWTH)):
            high, low = fallen(frame - back)
            over_high, over_low = high[:, 1] - under_feet, low[:, 1] - under_feet
            crossed = (over_high > 0.0) & (over_low <= 0.0)
            share = (over_high[crossed] / (over_high[crossed] - over_low[crossed]))[:, None]
            landed.append(high[crossed] + (low[crossed] - high[crossed]) * share)
        landed = np.concatenate(landed)
        landed, landed_at = landed[:, [0, 2]], landed[:, 1]
        heights = [holder.GetLocalTransformation(frame).ExtractTranslation()[1] for holder in holders]
        seen = [holder for holder, height in zip(holders, heights) if height == 0.0]
        assert len(seen) == 1 and np.allclose(sorted(heights)[:-1], rainfall.HIDDEN)
        crowns = np.asarray(UsdGeom.Mesh(seen[0].GetPrim().GetChild("crowns")).GetPointsAttr().Get()).reshape(-1, 4, 3)
        blades = ((crowns[:, 0] + crowns[:, 1]) / 2.0)[:, [0, 2]]
        apart = np.linalg.norm(blades[:, None] - landed[None], axis=2)
        reach = rainfall.SPLASH_WIDE[1] * max(wide for wide, _ in rainfall.SPLASH_GROWTH)
        assert len(landed) and apart.min(axis=1).max() < reach and apart.min(axis=0).max() < reach
        stood = crowns[:, :, 1] - landed_at[apart.argmin(axis=1)][:, None]  # over its drop's own ground
        assert np.abs(stood[:, :2] - 0.002).max() < 5e-3 and stood.max() < 0.05 and np.all(now[:, 1] <= before[:, 1] + 1e-6)
    under = place_build.ground_surface(stage, "yard", [[[60.0, 60.0], [64.0, 64.0]]])
    ruts = np.asarray(UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Effects/ruts/ruts")).GetPointsAttr().Get())
    assert laid["counts"]["streaks"] == 96 and effect.GetAttribute("score:role").Get() == "effect"
    assert slid[0][1] == 0.0 and slid[1][1] < -2.9 and slid[1][0] < -0.2 and slid[2][1] == 0.0
    assert streaks[:, 1].max() > 5.5 and streaks[:, 0].min() > 59.9
    over = ruts[:, 1] - under(ruts[:, 0], ruts[:, 2])
    assert np.isclose(under([62.0], [62.0])[0], place_build.ground_height(stage, "yard", 62.0, 62.0), atol=1e-4)
    assert tracked["counts"]["prints"] == 6 and over.min() >= ground_tracks.LIFT - 1e-4
    assert over.max() >= ground_tracks.BERM_HIGH
    assert stage.GetPrimAtPath("/yard/Effects/ruts").GetAttribute("score:surface").Get() == "surface/sand@1"
    place_build.remove(folder, "ruts")
    assert not Usd.Stage.Open(str(folder / "scene.usda")).GetPrimAtPath("/yard/Effects/ruts")


def reviewed(folder):
    """The review's region, views, projection and fault marks on the laid scene (no Blender)."""
    objects = review.scene_objects(folder)
    region = review.region_of(objects, box=(-6.0, -6.0, 6.0, 6.0))
    compartments = review.compartments_of({}, objects, region)
    door = {"name": "airlock", "address": "model/airlock_door", "low": np.array([4.0, 0.0, -1.0]),
            "high": np.array([5.0, 2.0, 1.0]), "ground": False}
    region["names"].append("airlock")
    views = review.views_of(region, compartments, review.doors_of(objects + [door], region),
                            review.floor_of(objects, compartments, region))
    left_out = {"plain", "sky", "floor", "regolith", "tunnel"}
    assert {"wall", "crate", "dome"} <= set(region["names"]) and not left_out & set(region["names"])
    assert [part["name"] for part in compartments] == ["dome"]
    assert [view["name"] for view in views] == ["plan", "corner_wn", "corner_en", "corner_es", "corner_ws",
                                                "door_airlock", "middle", "part_dome"]
    plan, door_view = views[0], views[5]
    assert np.isclose(plan["eye"][1] - plan["near"], review.CUT) and np.allclose(door_view["eye"][1], review.EYE)
    size = (400, 300)
    middle = (np.array(plan["aim"]))
    seen, _ = review.projected(plan, size, [middle, middle + [1, 0, 0], middle + [0, 0, 1]])
    scale = size[0] / plan["ortho"]
    assert np.allclose(seen, [[200, 150], [200 + scale, 150], [200, 150 + scale]])
    assert np.allclose(review.projected(door_view, size, [door_view["aim"]])[0], [[200, 150]])
    (folder / review.CHECK).write_text(json.dumps({"faults": [{"object": "crate", "kind": "floating"}]}))
    faults = review.faults_of(folder)
    marked = np.asarray(review.annotated(Image.new("RGB", size), plan, objects, region, faults))
    crate = review.projected(plan, size, [[3.0, 0.0, 0.0], [4.0, 0.0, 0.5]])[0].round().astype(int)
    red = (marked[..., 0] > 200) & (marked[..., 1] < 50) & (marked[..., 2] < 50)
    around = red[crate[0][1] - 2:crate[1][1] + 3, crate[0][0] - 2:crate[1][0] + 3].sum()
    assert faults == {"crate": "floating"} and around > 10 and red.sum() == around


def gltf_of(out, scene, name):
    """A packaged object's glTF document and its materials by name."""
    document = json.loads((out / scene["objects"][name]["file"]).read_text())
    return document, {material["name"]: material for material in document.get("materials", [])}


def packaged(folder, out):
    """The laid scene as a scene package (score.scene v1, package.py's check sound): every copy's model, stood by its
    matrix, fills the laid object's box; two copies in one surface one object, a copy stretched unevenly its own; a
    glTF model laid unchanged its library glTF as it was; a look's colour, a part's look, a tinted image surface's
    map box-projected over its tile; a palette recipe baked into its own unwrapped maps (on a laid ground one tile
    box-projected), its pictures on its look in its object's buffer; a see-through look as glTF transmission tinted
    as the preview's thin glass; each copy's collider from the physics check's roles, a prop's mass from its entry's
    record times its scale cubed; the lamps; the place's night, sun, grade (its view drawn as a lattice picture) and
    ground albedo; a mesh with no normals of its own smooth, as Blender shades it; a sliver xatlas charts nowhere
    kept; every look double sided; the characters (one under Characters), the rain and the sky named as left out."""
    from score.stages.place_build import scene_package
    place_build.put(folder, "wall2", "kit/box_piece", at=(30, 0, 30), turn=(0, 45, 0))
    place_build.surface(folder, "wall2", "surface/steel")
    place_build.put(folder, "plank", "kit/box_piece", at=(90, 0, 0), scale=(2, 1, 1))
    place_build.put(folder, "big", "kit/box_piece", at=(95, 0, 0), scale=(2, 2, 2))
    place_build.surface(folder, "big", "palette/hull_paint")
    place_build.surface(folder, "plank", "palette/smoked")
    place_build.surface(folder, "regolith", "surface/steel")  # a variant: its material referenced
    place_build.surface(folder, "regolith", "palette/hull_paint")
    held, _ = place_build.opened(folder)
    assert not held.GetPrimAtPath(f"/{held.GetDefaultPrim().GetName()}/Looks/regolith").HasAuthoredReferences()
    place_build.surface(folder, "tunnel", "surface/glass")
    sand = folder / "assets/surface/sand/1"
    Image.new("RGB", (62, 62), (90, 90, 90)).save(sand / "colour.jpg")  # over HELD_TEXELS: held at its 31, as 32
    (sand / "surface.json").write_text(json.dumps({"tile_metres": 0.5}))
    (folder / "assets/kit/box_piece/1/box_piece.json").write_text(json.dumps({"physics": {"mass_kg": 12.5}}))
    (folder / "ready.json").write_text(json.dumps({"roles": {"big": "prop", "wall": "structure", "sky": "light"}}))
    asked = []

    def baker(out, jobs):  # bake_looks.py's pictures, as Blender writes them, at each map's size
        for job in jobs:
            asked.append(job)
            for picture in job["pictures"].values():
                Image.new("RGB", tuple(job["size"]), (128, 128, 255)).save(out / "objects" / picture)

    scene_package.DENSITY, scene_package.LARGEST = 24, 64  # maps held small, so the panel needs more than one
    scene_package.HELD_TEXELS = 32  # the game's side, under a map's: its pictures taken down
    graded = []

    def grader(out, environment):  # grade_lut.py's lattice picture, for the view the render grades through
        graded.append((environment["view_transform"], environment["look"]))
        (out / scene_package.GRADE_FILE).parent.mkdir(exist_ok=True)
        Image.new("RGB", (8 * 8, 8)).save(out / scene_package.GRADE_FILE)

    laid = Usd.Stage.Open(str(folder / "scene.usda"))
    UsdSkel.Root.Define(laid, "/yard/Characters/crew")  # a character laid beside the objects, as the walkers' layer
    cast_skinned(laid, folder)
    laid.Save()
    (out / scene_package.BAKE).mkdir(parents=True)
    (out / scene_package.BAKE / "kept.done").touch()  # a stopped bake's map, for the next bake to keep or drop
    (out / "old.json").touch()
    events, held_written, held_glb = [], scene_package.written, scene_package.skinned.character_glb
    scene_package.written = lambda out, name, glb: events.append(("written", name)) or held_written(out, name, glb)
    scene_package.skinned.character_glb = lambda root, baked=None: events.append(
        ("made", str(root.GetPath()))) or held_glb(root, baked)
    try:
        made = scene_package.packaged(folder, out, baker, grader)
    finally:
        scene_package.written, scene_package.skinned.character_glb = held_written, held_glb
    dune_prim = held.GetPrimAtPath(f"/{held.GetDefaultPrim().GetName()}/Objects/dune")
    assert {look["material"].baseColorTexture.size for look in scene_package.looks_of(dune_prim).values()
            if look["material"].baseColorTexture is not None} == {(32, 32)}  # a look holds what the package writes
    scene_package.DENSITY, scene_package.LARGEST, scene_package.HELD_TEXELS = 512, 4096, 2048
    # a character at a time: the leader written before the crowd's first person is made, so no two are held at once
    assert events.index(("written", "leader")) < next(at for at, (what, path) in enumerate(events)
                                                      if what == "made" and "crowd" in path), events
    assert (out / scene_package.BAKE / "kept.done").is_file() and not (out / "old.json").exists()
    scene = json.loads((out / "scene.json").read_text())
    copies = {copy["name"]: copy for copy in scene["instances"]}
    boxes = {item["name"]: np.array(item["box"]) for item in place_build.listing(folder)["objects"]}
    for name, copy in ((name, copy) for name, copy in copies.items() if copy["kind"] != "character"):
        model = trimesh.load(out / scene["objects"][copy["object"]]["file"], force="mesh")
        model.apply_transform(np.array(copy["matrix"]).reshape(4, 4).T)
        assert np.abs(model.bounds - boxes[name]).max() < 2e-3, (name, model.bounds, boxes[name])
    _, crate = gltf_of(out, scene, copies["crate"]["object"])
    dune, dune_looks = gltf_of(out, scene, copies["dune"]["object"])
    dune_uv = dune["accessors"][dune["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]]
    assert made["check"] == "sound" and scene_package.package.problems(out) == []
    holed = trimesh.load(out / scene["objects"][copies["holed"]["object"]]["file"], force="mesh", process=False)
    _, first, per_point = np.unique(holed.vertices.round(5), axis=0, return_index=True, return_inverse=True)
    assert np.allclose(holed.vertex_normals, holed.vertex_normals[first][per_point.ravel()], atol=1e-3)
    assert copies["wall2"]["object"] == copies["wall"]["object"] != copies["floor"]["object"]
    assert copies["big"]["scale"] == 2.0 and copies["big"]["object"] == copies["panel"]["object"] != "big"
    assert copies["plank"]["scale"] == 1.0 and scene["objects"][copies["plank"]["object"]]["size"] == [2.0, 2.0, 0.5]
    assert {copies[name]["object"] for name in ("cabinet", "shelf", "stone")} == {"cabinet"}
    assert scene["objects"]["cabinet"]["route"] == "library glTF" and scene["objects"]["dune"]["route"] != "library glTF"
    assert np.allclose(crate["surface/boards@1"]["pbrMetallicRoughness"]["baseColorFactor"], (1, 0, 0, 1))
    assert crate["surface/boards@1"]["doubleSided"] is True  # an opaque look drawn from both sides, as Cycles draws it
    assert np.allclose(crate["surface/steel@1 top"]["pbrMetallicRoughness"]["baseColorFactor"], (0.3, 0.3, 0.4, 1))
    sand_look = dune_looks["surface/sand@1"]["pbrMetallicRoughness"]
    assert np.allclose(sand_look["baseColorFactor"], (1.0, 0.2158605, 0.0, 1.0)) and "baseColorTexture" in sand_look
    assert np.allclose(np.array(dune_uv["max"]) - dune_uv["min"], 2.0 / 0.5)  # the 2 m box over a 0.5 m tile
    assert copies["big"]["collider"] == {"shape": "convex hull", "dynamic": True, "mass_kg": 100.0}
    assert copies["wall"]["collider"] == {"shape": "mesh", "dynamic": False} and copies["crate"]["collider"] is None
    assert [(lamp["name"], lamp["kind"]) for lamp in scene["lamps"]] == [("bulb", "point"), ("sun", "sun"),
                                                                         ("moon", "sun")]
    bulb = scene["lamps"][0]
    assert np.isclose(bulb["strength"], bulb["intensity"] * np.pi) and bulb["watts"] == bulb["strength"]
    assert np.isclose(scene["lamps"][2]["strength"], scene["lamps"][2]["intensity"] * 4.0)  # the render's sun units
    assert {"walker", "rain", "sky", "crew"} <= {item["name"] for item in scene["left_out"]}
    skinned_characters(folder, out, scene, copies)
    panel, panel_looks = gltf_of(out, scene, copies["panel"]["object"])
    ground, ground_looks = gltf_of(out, scene, copies["regolith"]["object"])
    _, tunnel_looks = gltf_of(out, scene, copies["tunnel"]["object"])
    maps = [look for name, look in panel_looks.items() if name.startswith("surface/boards@1")]
    ground_uv = ground["accessors"][ground["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]]
    tiles = [job["tile"] for job in asked]
    assert len(maps) > 1 and all("baseColorTexture" in look["pbrMetallicRoughness"] and "normalTexture" in look
                                 and "extras" not in look for look in maps)
    assert panel["images"] and all(set(image) == {"bufferView", "mimeType"} for image in panel["images"])
    held = held_pictures(out, scene)
    assert held and max(max(size) for size, _, _ in held) == 32 and all(count == 1 for _, count, _ in held), held
    assert all(side % scene_package.BLOCK_TEXELS == 0 for size, _, _ in held for side in size), held  # DXT blocks
    assert any(reading == 2 for _, _, reading in held)  # the baker's like metal-roughness and normal: one picture
    assert not (out / "objects" / scene_package.TEXTURES).exists()  # every picture rides in its object's buffer
    assert made["baked_maps"] == len(asked) and tiles.count(scene_package.GROUND_TILE) == 1
    assert all(max(job["size"]) <= 64 and job["spec"]["seed"] == 3 and job["texels_a_metre"] >= 24
               for job in asked if not job["tile"])
    assert np.allclose(np.array(ground_uv["max"]) - ground_uv["min"], 6.0 / scene_package.GROUND_TILE, atol=0.01)
    assert "baseColorTexture" in ground_looks["surface/boards@1"]["pbrMetallicRoughness"]
    glass = tunnel_looks["surface/glass@1"]
    assert np.allclose(glass["pbrMetallicRoughness"]["baseColorFactor"], (0.9, 0.9, 1.0, 0.2))
    assert glass["extensions"] == {"KHR_materials_transmission": {"transmissionFactor": 0.8},
                                   "KHR_materials_ior": {"ior": 1.5}} and glass["alphaMode"] == "BLEND"
    _, plank_looks = gltf_of(out, scene, copies["plank"]["object"])
    _, big_looks = gltf_of(out, scene, copies["big"]["object"])
    smoked = next(look for name, look in plank_looks.items() if name.startswith("surface/glass@1"))
    assert smoked["alphaMode"] == "BLEND" and smoked["extensions"]["KHR_materials_transmission"] == {
        "transmissionFactor": 0.5}  # a palette glass seen through, as its variant's opacity says
    assert all(look.get("alphaMode", "OPAQUE") == "OPAQUE" for look in big_looks.values())  # a paint stays opaque
    world = scene["environment"]
    assert world["exposure"] == np.float32(2.5) and world["sky"] is None and world["night"]["moon"]["elevation"] == 30
    assert np.isclose(world["night"]["moon"]["strength"], 0.04)  # 0.01 laid, times 4 as Blender's reader reads it
    assert world["sun"]["elevation"] == 30 and world["sun"]["heading"] == 0 and world["view_transform"] == "AgX"
    assert world["look"] == "AgX - Medium High Contrast" and np.allclose(world["background"], (0.01, 0.04, 0.08))
    assert np.allclose(world["ground_albedo"], (0.2158605, 0.2158605, 1.0), atol=1e-5)  # the tile's (128, 128, 255)
    square = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 0], [2, 1e-5, 0], [2.00001, 0, 0]], float)
    sliver = scene_package.unwrapped(square, np.tile([0.0, 0.0, 1.0], (7, 1)),
                                     np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5]]))
    assert sum(len(laid[3]) for laid in sliver) == 3  # every triangle kept, so the model check counts them all
    assert graded == [("AgX", "AgX - Medium High Contrast")] and (out / world["grade"]["file"]).is_file()
    assert world["grade"]["size"] == 64 and world["grade"]["middle"] == 0.18 and world["grade"]["display"] == "sRGB"


def drafted(folder, out):
    """The laid scene as a draft package (`package --draft`): nothing baked, the palette recipe on the panel its look's
    plain colour in one map, the sand's image surface keeping its picture, scene.json marked draft, the check sound."""
    from score.stages.place_build import scene_package

    def baker(out, jobs):
        raise AssertionError(f"a draft asked for {len(jobs)} bakes")

    def grader(out, environment):
        (out / scene_package.GRADE_FILE).parent.mkdir(exist_ok=True)
        Image.new("RGB", (8 * 8, 8)).save(out / scene_package.GRADE_FILE)

    made = scene_package.packaged(folder, out, baker, grader, draft=True)
    scene = json.loads((out / "scene.json").read_text())
    copies = {copy["name"]: copy for copy in scene["instances"]}
    _, panel_looks = gltf_of(out, scene, copies["panel"]["object"])
    _, dune_looks = gltf_of(out, scene, copies["dune"]["object"])
    boards = [look for name, look in panel_looks.items() if name.startswith("surface/boards@1")]
    assert made["draft"] is True and made["baked_maps"] == 0 and scene["draft"] == scene_package.DRAFT, scene.get("draft")
    assert len(boards) == 1 and "baseColorTexture" not in boards[0]["pbrMetallicRoughness"] and "extras" not in boards[0]
    assert "baseColorTexture" in dune_looks["surface/sand@1"]["pbrMetallicRoughness"]
    assert scene_package.package.problems(out) == []


def pieced(folder, root, out):
    """The laid scene as a piece list (score.scene v2, `package --pieces`), with no Blender: each library piece once by
    its address and its index's digest, no file of it written; a made piece (the kerb's blocks) as a GLB of one mesh a
    part, no material and no texture coordinates, two laid copies of one content one piece; every copy, its piece
    stood by its whole matrix (a stretch kept in it), filling its laid box; a palette look's spec word for word, a
    part's own look, an image surface's map as its library reference, a glTF model's own texture; the characters
    skinned; the check sound, and refusing a stale digest, a withdrawn entry, a made file changed and a part with no
    look."""
    from score.stages.place_build import pieces, scene_package
    import package
    (root / "index").mkdir(exist_ok=True)
    rows = {}
    for record in (json.loads(path.read_text()) for path in sorted(root.glob("entries/*/*/*/entry.json"))):
        rows.setdefault(record["kind"], []).append({"address": record["address"], "digest": f"d-{record['address']}",
                                                    "state": "draft"})
    for kind, entries in rows.items():
        (root / "index" / f"{kind}.json").write_text(json.dumps({"schema": "score-lib-index/1", "kind": kind,
                                                                  "entries": entries}))
    held_baked, held_graded = scene_package.blender_baked, scene_package.blender_graded
    scene_package.blender_baked = scene_package.blender_graded = None  # never called: a call fails the test
    place_build.put(folder, "kerb2", "kit/box_piece", at=(50, 0, 52))
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    kerb = stage.GetPrimAtPath("/yard/Objects/kerb")
    copied = stage.DefinePrim("/yard/Objects/kerb_copy", "Xform")
    copied.GetReferences().AddInternalReference(kerb.GetPath())
    UsdGeom.Xformable(copied).ClearXformOpOrder()
    UsdGeom.Xformable(copied).AddTranslateOp().Set(Gf.Vec3d(50, 0, 60))
    stage.Save()
    try:
        made = pieces.packaged(folder, out)
    finally:
        scene_package.blender_baked, scene_package.blender_graded = held_baked, held_graded
    scene = json.loads((out / "scene.json").read_text())
    copies = {copy["name"]: copy for copy in scene["copies"]}
    boxes = {item["name"]: np.array(item["box"]) for item in place_build.listing(folder)["objects"]}
    place_build.remove(folder, "kerb2")
    place_build.remove(folder, "kerb_copy")
    for name, copy in ((name, copy) for name, copy in copies.items() if copy["kind"] != "character"):
        piece = scene["pieces"][copy["piece"]]
        if "made" in piece:
            model = trimesh.load(out / piece["made"], force="mesh")
            model.apply_transform(np.array(copy["matrix"]).reshape(4, 4).T)
            assert np.abs(model.bounds - boxes[name]).max() < 2e-3, (name, model.bounds, boxes[name])
    glb = (out / "made/kerb.glb").read_bytes()
    document = json.loads(glb[20:20 + int.from_bytes(glb[12:16], "little")])
    spec = json.loads(stage.GetPrimAtPath("/yard/Looks/panel").GetAttribute("score:recipe:spec").Get())
    assert made["check"] == "sound" and scene["version"] == 2 and not list(out.glob("objects")), made
    assert copies["kerb_copy"]["piece"] == copies["kerb"]["piece"] == "kerb" and copies["kerb2"]["piece"] == "box_piece"
    assert sorted(path.name for path in (out / "made").iterdir()) == sorted(
        f"{name}.glb" for name, piece in scene["pieces"].items() if "made" in piece)
    assert scene["pieces"]["box_piece"] == {"library": "kit/box_piece@1", "digest": "d-kit/box_piece@1",
                                            "parts": ["geo", "rim", "top"], "size": [1.0, 2.0, 0.5], "triangles": 14}
    assert scene["pieces"]["cup"]["library"] == "take/cup@1" and copies["cabinet"]["looks"] == {
        "door": "own-cabinet", "part_0": "own-cabinet"}  # a glTF model in its own bake
    assert sorted(mesh["name"] for mesh in document["meshes"]) == ["kerb", "line"] and "materials" not in document
    assert all(set(primitive["attributes"]) == {"POSITION", "NORMAL"} and "material" not in primitive
               for mesh in document["meshes"] for primitive in mesh["primitives"])
    assert copies["plank"]["piece"] == copies["crate"]["piece"] and copies["plank"]["matrix"][:3] == [2.0, 0.0, 0.0]
    assert scene["looks"][copies["panel"]["looks"]["geo"]] == {"library": "surface/boards@1", "spec": spec}
    assert scene["looks"][copies["crate"]["looks"]["top"]]["library"] == "surface/steel@1" != scene["looks"][
        copies["crate"]["looks"]["geo"]]["library"]
    assert scene["looks"][copies["dune"]["looks"]["top"]]["maps"]["diffuseColor"]["file"] == "surface/sand@1/colour.jpg"
    assert copies["leader"]["looks"] == {"*": "own-leader"} and scene["pieces"]["leader"]["skinned"] is True
    assert copies["leader"]["plays"] and copies["big"]["collider"]["mass_kg"] == 100.0
    assert scene["environment"]["grade"] is None and scene["lamps"][0]["name"] == "bulb"
    index = json.loads((root / "index/kit.json").read_text())
    index["entries"][0]["digest"] = "changed"
    (root / "index/kit.json").write_text(json.dumps(index))
    (out / "made/kerb.glb").write_bytes(glb + b"    ")
    del copies["crate"]["looks"]["top"]
    (out / "scene.json").write_text(json.dumps(scene))
    found = package.problems(out)
    withdrawn = package.problems(out, held={"kit/box_piece@1": {"digest": "d-kit/box_piece@1", "state": "withdrawn"}})
    assert any("piece box_piece: its digest" in line for line in found), found
    assert any("kerb.glb does not hash" in line for line in found) and any(
        "(crate): its part top has no look" in line for line in found), found
    assert any("kit/box_piece@1 is withdrawn" in line for line in withdrawn), withdrawn


def held_pictures(out, scene):
    """Every packaged object's pictures as [(their size, how many of its images hold those bytes read alike, how many
    of its textures read it)]."""
    import io
    from score.stages.place_build import scene_package
    found = []
    for item in scene["objects"].values():
        document = json.loads((out / item["file"]).read_text())
        binary = (out / item["file"]).with_suffix(".bin").read_bytes() if document.get("buffers") else b""
        held = [binary[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]] for view in (
            document["bufferViews"][image["bufferView"]] for image in document.get("images", []))]
        read_as = scene_package.pictures_read_as(document)
        alike = [(data, read_as.get(number)) for number, data in enumerate(held)]
        found += [(Image.open(io.BytesIO(data)).size, alike.count(alike[number]),
                   sum(1 for texture in document["textures"] if texture["source"] == number))
                  for number, data in enumerate(held)]
    return found


def skinned_characters(folder, out, scene, copies):
    """The cast's skinned characters as skinned glTFs: the leader's skeleton, shown box, blend shape and clip (one
    round), its walk as node 0's moves in the animation it plays, its skin at the clip's first, middle and last keys
    within CLOSE of UsdSkel's (an inverse bind left unwritten fails it); the crowd's three copies, its two phases one
    object, each copy playing from its own start."""
    from score.stages.place_build import scene_package, skinned
    assert "leader" in copies, scene["left_out"]
    leader = scene["objects"][copies["leader"]["object"]]
    assert leader["route"] == "skinned from the laid USD" and leader["check"]["pass"], leader["check"]
    assert leader["check"]["skinned_error"] < 1e-5 and leader["clips"] == {"standing": round(2.0 / 30.0, 6)}
    document, _ = gltf_of(out, scene, copies["leader"]["object"])
    assert [document["nodes"][joint]["name"] for joint in document["skins"][0]["joints"]] == ["hips", "chest"]
    assert len(document["meshes"]) == 1 and document["meshes"][0]["extras"]["targetNames"] == ["lean"]
    paths = {(channel["target"]["node"], channel["target"]["path"]) for channel in document["animations"][0]["channels"]}
    assert {(0, "translation"), (3, "rotation"), (4, "weights")} <= paths, sorted(paths)
    assert copies["leader"]["plays"] == {"animation": "standing", "starts": 0.0, "loops": True}
    assert copies["leader"]["at"] == [5.0, 0.0, 5.0]
    crowd = [copies[f"crowd_{number}"] for number in range(3)]
    assert len({copy["object"] for copy in crowd}) == 1 and [copy["at"][0] for copy in crowd] == [20.0, 21.0, 22.0]
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    assert [copy["plays"]["starts"] for copy in crowd] == [0.0, -1.0 / stage.GetTimeCodesPerSecond(), 0.0]
    root = stage.GetPrimAtPath("/yard/Characters/leader")
    glb, facts = skinned.character_glb(root)
    unbound = tampered(glb, scene_package.unpacked(glb, None)[0]["skins"][0]["inverseBindMatrices"])
    assert skinned.check_of(root, glb, facts)["pass"] and not skinned.check_of(root, unbound, facts)["pass"]


def resumed(out):
    """A bake in runs of at most BATCH maps of one object: a run killed partway (the memory cap's exit 247) is refused
    naming the maps not baked; a changed object's finished maps are baked again; the next bake runs only the maps
    not finished, each map's pictures then in place and its mark gone."""
    from score.stages.place_build import scene_package
    (out / "objects").mkdir(parents=True)
    jobs = []
    for name, maps in (("panel", 3), ("door", 1)):
        (out / f"objects/{name}.bin").write_bytes(name.encode())
        (out / f"objects/{name}.gltf").write_text(json.dumps({"buffers": [{"uri": f"{name}.bin"}]}))
        jobs += [{"gltf": f"objects/{name}.gltf", "mesh": f"part_{number}", "size": [8, 8],
                  "pictures": {kind: f"textures/{name}_{number}_{kind}.png" for kind in scene_package.PICTURES}}
                 for number in range(maps)]
    runs, stop, refused = [], [2], []

    def run(out, listing, log):  # bake_looks.py: each map's pictures and mark, killed after `stop` maps
        handed = json.loads(listing.read_text())
        runs[-1].append([(job["gltf"][8:-5], job["mesh"][5:]) for job in handed["jobs"]])
        for job in handed["jobs"]:
            if stop[0] == 0:
                return 247
            stop[0] -= 1
            for kind in scene_package.PICTURES:
                Image.new("RGB", (8, 8)).save(pathlib.Path(handed["into"]) / f"{job['key']}_{kind}.png")
            (pathlib.Path(handed["into"]) / f"{job['key']}.done").touch()
        return 0
    scene_package.BATCH, scene_package.SIDE_BY_SIDE = 2, 1
    for left, change in ((2, None), (1, "panel"), (99, None)):
        if change:
            (out / f"objects/{change}.bin").write_bytes(b"moved")
        stop[0] = left
        runs.append([])
        try:
            scene_package.blender_baked(out, jobs, run)
        except place_build.Refused as why:
            refused.append(str(why).split(";")[0])
    scene_package.BATCH, scene_package.SIDE_BY_SIDE = 6, 2
    placed = all((out / "objects" / picture).is_file() for job in jobs for picture in job["pictures"].values())
    assert refused == ["the bake failed (exit 247, 2 of 4 maps not baked",
                       "the bake failed (exit 247, 3 of 4 maps not baked"], refused
    assert runs == [[[("panel", "0"), ("panel", "1")], [("panel", "2")]],
                    [[("panel", "0"), ("panel", "1")]],
                    [[("panel", "1"), ("panel", "2")], [("door", "0")]]], runs
    assert placed and not any((out / scene_package.BAKE).iterdir())


def side_by_side(out):
    """A bake's runs held SIDE_BY_SIDE at once (one object's maps a run, two of them on the card together), every map
    then in place, the runs' logs all in blender.log and their listings gone; a run asks the card queue for the bake's
    own measured share of the card and of the memory."""
    import threading
    from score.stages.place_build import scene_package
    (out / "objects").mkdir(parents=True)
    jobs = []
    for name in ("panel", "door", "hatch"):
        (out / f"objects/{name}.gltf").write_text(json.dumps({"buffers": []}))
        jobs.append({"gltf": f"objects/{name}.gltf", "mesh": "part_0", "size": [8, 8],
                     "pictures": {kind: f"textures/{name}_{kind}.png" for kind in scene_package.PICTURES}})
    together, most, turn = [0], [0], threading.Condition()

    def run(out, listing, log):  # bake_looks.py: its map's pictures and mark, waiting a while for another run beside it
        with turn:
            together[0] += 1
            most[0] = max(most[0], together[0])
            turn.notify_all()
            turn.wait_for(lambda: together[0] > 1 or most[0] > 1, timeout=2)
        handed = json.loads(listing.read_text())
        for job in handed["jobs"]:
            for kind in scene_package.PICTURES:
                Image.new("RGB", (8, 8)).save(pathlib.Path(handed["into"]) / f"{job['key']}_{kind}.png")
            (pathlib.Path(handed["into"]) / f"{job['key']}.done").touch()
        log.open("a").write(f"BAKE DONE {len(handed['jobs'])} maps\n")
        with turn:
            together[0] -= 1
        return 0
    scene_package.blender_baked(out, jobs, run)
    placed = all((out / "objects" / picture).is_file() for job in jobs for picture in job["pictures"].values())
    told = (out / "bake/blender.log").read_text()
    assert most[0] == 2 and placed and told.count("BAKE DONE") == 3, (most, placed, told)
    assert not list((out / "bake").glob("jobs-*.json")) and not list((out / "bake").glob("run-*.log"))
    command = render.queued("job", "script.py", [], card_gb=scene_package.BAKE_CARD_GB,
                            memory_gb=scene_package.BAKE_MEMORY_GB)
    asked = command[:command.index("--priority")]
    assert asked[-4:] == ["--card-gb", "4", "--memory-gb", "6"], asked


def sized_and_timed(out):
    """A baked part's maps each as big as its charts at DENSITY and at most LARGEST, never under DENSITY: a 12 m panel
    of two faces (each wider than a map; the base's hangar hung 11.5 h packing such faces) cut and spread on many
    maps, a 1 m tile on one map its own size, the panel seen only from 100 m on maps at LEAST_DENSITY; a package step past its time stops the process loudly, named in its
    log, one in time goes on; a bake run's Blender runs under its timeout, one stopped there refused saying so."""
    import subprocess
    import sys
    from score.stages.place_build import scene_package
    scene_package.DENSITY, scene_package.LARGEST = 24, 64
    try:
        laid = {}
        for name, side in (("panel", 12.0), ("tile", 1.0)):
            square = np.array([[0, 0, 0], [side, 0, 0], [side, side / 2, 0], [0, side / 2, 0]], float)
            laid[name] = scene_package.unwrapped(square, np.tile([0.0, 0.0, 1.0], (4, 1)), np.array([[0, 1, 2],
                                                                                                    [0, 2, 3]]))
        panel = np.array([[0, 0, 0], [12.0, 0, 0], [12.0, 6.0, 0], [0, 6.0, 0]], float)
        laid["far"] = scene_package.unwrapped(panel, np.tile([0.0, 0.0, 1.0], (4, 1)), np.array([[0, 1, 2], [0, 2, 3]]),
                                              np.array([[6.0, 3.0, 100.0]]))
        laid["unseen"] = scene_package.unwrapped(panel, np.tile([0.0, 0.0, 1.0], (4, 1)), np.array([[0, 1, 2], [0, 2, 3]]),
                                                 np.zeros((0, 3)))
    finally:
        scene_package.DENSITY, scene_package.LARGEST = 512, 4096
    panel_area = sum(scene_package.areas_of(points, faces).sum() for points, _, _, faces, _, _ in laid["panel"])
    assert len(laid["panel"]) > 10 and np.isclose(panel_area, 72.0), (len(laid["panel"]), panel_area)
    assert all(max(size) <= 64 and texels >= 24 * scene_package.HELD_SHARE
               for name, maps in laid.items() if name not in ("far", "unseen") for *_, size, texels in maps), laid
    assert all(16 * scene_package.HELD_SHARE <= texels < 24 * scene_package.HELD_SHARE
               for name in ("far", "unseen") for *_, texels in laid[name]), \
        {name: [texels for *_, texels in laid[name]] for name in ("far", "unseen")}
    assert len(laid["tile"]) == 1 and max(laid["tile"][0][4]) < 64, laid["tile"][0][4:]
    out.mkdir(parents=True)
    step = ("import pathlib, sys, time; from score.stages.place_build import scene_package as package; "
            "package.STEP_SECONDS['object'] = 1; out = pathlib.Path(sys.argv[1]); seconds = float(sys.argv[2])\n"
            "with package.deadline(out, 'stuck', 'object'):\n    time.sleep(seconds)\ntime.sleep(2); print('went on')")
    runs = {name: subprocess.Popen([sys.executable, "-c", step, str(out / name), seconds], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, cwd=place_build.REPO)
            for name, seconds in (("late", "30"), ("timely", "0"))}
    ended = {name: (run.wait(timeout=40), *run.communicate()) for name, run in runs.items()}
    assert ended["late"][0] != 0 and "Timeout" in ended["late"][2] and "went on" not in ended["late"][1], ended
    assert ended["timely"][:2] == (0, "went on\n"), ended
    assert (out / "late" / scene_package.STEPS).read_text() == "object stuck: stopped past 1 s\n"
    command = render.queued("job", "script.py", [], card=False, seconds=scene_package.STEP_SECONDS["bake run"])
    assert command[command.index("timeout"):command.index(str(render.BLENDER))] == ["timeout", "-k", "30", "1800"]
    (out / "objects").mkdir()
    (out / "objects/door.gltf").write_text(json.dumps({"buffers": []}))
    job = {"gltf": "objects/door.gltf", "mesh": "part_0", "size": [8, 8],
           "pictures": {kind: f"textures/door_{kind}.png" for kind in scene_package.PICTURES}}
    try:
        scene_package.blender_baked(out, [job], lambda out, listing, log: render.TIMED_OUT)
        refused = None
    except place_build.Refused as why:
        refused = str(why)
    assert refused and refused.startswith("the bake failed (exit 124, its run stopped past 1800 s, 1 of 1"), refused


def stilled(folder):
    """A still's scene (render.still_stage) holds every laid object as the scene does, its assets read from the
    place's folder, and none of the walkers' layer's people; the scene keeps its walkers."""
    walkers = folder / "layers/walkers/layers/characters.usda"
    walkers.parent.mkdir(parents=True)
    people = Usd.Stage.CreateNew(str(walkers))
    UsdSkel.Root.Define(people, "/yard/Characters/walker_one")
    people.Save()
    laid = Sdf.Layer.FindOrOpen(str(place_build.scene_path(folder)))
    laid.subLayerPaths.append("layers/walkers/layers/characters.usda")
    laid.Save()
    still = Usd.Stage.Open(str(render.still_stage(folder)))
    scene = Usd.Stage.Open(str(place_build.scene_path(folder)))
    shown = {str(prim.GetPath()) for prim in still.Traverse()}
    whole = {str(prim.GetPath()) for prim in scene.Traverse()}
    assert whole - shown == {"/yard/Characters/walker_one"} and len(shown) > 100, sorted(whole - shown)[:5]


def filmed(tmp_path):
    """A film's path on a lane walled across but for a gap: still on the concept's view first, round the wall
    (never through it) at eye height, every frame clear of every solid, and slowing to a stop at its end. A door in
    the gap is a solid to the camera while shut, and stands open when marked score:opens (a walker comes through)."""
    folder = tmp_path / "lane"
    place_build.start(folder, "lane", tmp_path / "concept.png")
    place_build.blocks(folder, "road", [[-12, -0.3, -12, 12, 0, 30, "road"]], ground=True)
    place_build.blocks(folder, "wall", [[-12, 0, 9.5, 1, 3, 10.5, "wall"]])
    place_build.camera(folder, (0, 8, -12), (0, 0, 10), 40)
    made = film.path(folder, ["-4,4", "-4,16>-4,1.6,30"], seconds=6.0)
    frames = json.loads((folder / "film" / "path.json").read_text())["views"]
    eyes = np.array([frame["eye"] for frame in frames])
    crossing = eyes[np.abs(eyes[:, 2] - 10.0) < 0.6]
    steps = np.linalg.norm(np.diff(eyes, axis=0), axis=1)
    assert made["frames"] == 6 * film.FPS == len(frames) and made["frames_too_near"] == 0
    assert np.allclose(eyes[:film.FPS], [0, 8, -12], atol=0.05) and frames[0]["fov"] == 40
    assert np.allclose(frames[0]["aim"], np.array([0, 8, -12]) + 10 * np.array([0, -8, 22]) / np.hypot(8, 22), atol=0.01)
    assert len(crossing) and (crossing[:, 0] > 1.0 + film.CLEAR).all() and np.isclose(eyes[-1, 1], film.EYE, atol=0.01)
    assert made["least_clearance"] >= film.CLEAR and steps[-3:].max() < steps.max() / 4
    place_build.blocks(folder, "door", [[1, 0, 9.9, 3, 2.5, 10.1, "door"]])
    seen = []
    for mark in ("", "swings"):
        stage, place = place_build.opened(folder)
        door = stage.GetPrimAtPath(f"/{place}/Objects/door")
        door.CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set("door")
        door.CreateAttribute("score:opens", Sdf.ValueTypeNames.String).Set(mark)
        stage.GetRootLayer().Save()
        seen.append(film.camera_paths.first_hits(film.place_scenes(folder)["blocking"], np.array([[2.0, 1.2, 8.0]]),
                                                 np.array([[0.0, 0.0, 1.0]]))[0])
    assert np.isclose(seen[0], 1.9, atol=0.01) and np.isinf(seen[1]), seen
    place_build.camera_cut(folder, "wall")  # the camera sees through the wall; it still stands for the walkers
    through = film.camera_paths.first_hits(film.place_scenes(folder)["blocking"], np.array([[-4.0, 1.2, 8.0]]),
                                           np.array([[0.0, 0.0, 1.0]]))[0]
    place_build.view(folder, "outside", eye=(0, 20, 30), aim=(0, 0, 0), fov=60)
    place_build.view(folder, "section", eye=(-4, 1.6, 8), aim=(-4, 1.6, 0), fov=60, cut=True)
    cuts = {view["name"]: view["cut"] for view in render.views(place_build.record_of(folder), 80,
                                                                ["outside", "section"])["views"]}
    assert np.isinf(through) and cuts == {"concept": ["wall"], "outside": [], "section": ["wall"]} \
        and "wall" in ready.solids(folder), (through, cuts)
    try:
        place_build.camera_cut(folder, "nothing")
        raise AssertionError("a cut of an object the scene does not hold was listed")
    except place_build.Refused:
        pass
    place_build.put(folder, "awning", "kit/box_piece", at=(-8, 0, 0))
    place_build.camera_cut(folder, "awning")
    place_build.remove(folder, "awning")  # a removed object leaves the cut too, which would name what is gone
    assert place_build.record_of(folder)["cut"] == ["wall"], place_build.record_of(folder)["cut"]



def doored(tmp_path):
    """An airlock laid with place_build: a capped tunnel (the chamber) joined to a second one (the base side), a door
    at the join and a hatch in the end wall. The package gives each door its leaf, hinge, limits, opening and opens
    mark, its sides read through it, and the chamber its inner and outer door and its air over the deck."""
    from score.stages.place_build import scene_package
    folder = tmp_path / "lock"
    place_build.start(folder, "lock", tmp_path / "concept.png")
    place_build.tube(folder, "chamber", 1.5, 3.0, hoops=3, cap=[1.6, 2.0])
    place_build.tube(folder, "porch", 1.5, 4.0, at=(0, 0, -4), hoops=3)
    place_build.blocks(folder, "inner_door", [[-0.5, 0, 0.0, 0.5, 2.0, 0.2, "door"]])
    place_build.blocks(folder, "outer_hatch", [[-0.6, 0, 2.84, 0.6, 2.0, 3.0, "door"]])
    stage, place = place_build.opened(folder)
    for name in ("inner_door", "outer_hatch"):
        stage.GetPrimAtPath(f"/{place}/Objects/{name}").CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set(
            "door")
    stage.GetPrimAtPath(f"/{place}/Objects/inner_door").CreateAttribute("score:opens", Sdf.ValueTypeNames.String).Set(
        "walkers")
    place_build.blocks(folder, "fan", [[0.5, 2.2, 1.0, 0.7, 2.4, 1.2, "fan"]], role="prop")
    for name, role in (("inner_door", "door"), ("fan", "prop")):  # keyed as walker_route keys a door's swing
        xform = UsdGeom.Xformable(stage.GetPrimAtPath(f"/{place}/Objects/{name}"))
        swing = xform.AddRotateYOp(opSuffix="swing")
        swing.GetAttr().Set(0.0, 5.0)
        swing.GetAttr().Set(90.0, 20.0)
        xform.SetXformOpOrder([swing, *[op for op in xform.GetOrderedXformOps() if op != swing]])
    stage.GetRootLayer().Save()
    scene = scene_package.write(folder, tmp_path / "lock_package")
    assert {"name": "fan", "why": "it moves over time: not converted"} in scene["left_out"], scene["left_out"]
    assert "inner_door" in {copy["name"] for copy in scene["instances"]}, scene["left_out"]  # a moving door at rest
    doors = {copy["name"]: copy["door"] for copy in scene["instances"] if "door" in copy}
    inner, outer = doors["inner_door"], doors["outer_hatch"]
    deck = scene_package.part_points(stage.GetPrimAtPath(f"/{place}/Objects/chamber"), "deck")[:, 1].max()
    low = 1.5 - deck  # the deck's top under the tube's axis
    segment = 1.5 ** 2 * (np.pi - np.arccos(low / 1.5)) + low * np.sqrt(1.5 ** 2 - low ** 2)  # the circle over it
    assert set(doors) == {"inner_door", "outer_hatch"} and inner["opens"] is True and outer["opens"] is False
    assert inner["between"] == ["chamber", "porch"] and outer["between"] == [None, "chamber"]
    assert (inner["side"], inner["leads"], outer["side"], outer["leads"]) == ("inner", "porch", "outer", None)
    assert inner["opening"]["in"] == outer["opening"]["in"] == "chamber" and outer["opening"]["end_wall"] is True
    assert inner["opening"]["end_wall"] is False and np.allclose(outer["opening"]["size"], [1.2, 2.0])
    assert all(door["move"] == "hinge" and door["axis"] == [0.0, 1.0, 0.0] and door["leaf"] == name
               and sorted([0.0, door["open"]]) == door["limits"] and abs(door["open"]) == 90.0
               and np.isclose(abs(door["pivot"][0]), door["opening"]["size"][0] / 2) for name, door in doors.items())
    [chamber] = scene["chambers"]
    assert (chamber["name"], chamber["inner"], chamber["outer"]) == ("chamber", ["inner_door"], ["outer_hatch"])
    assert segment * 3.0 < chamber["air_volume"] < 1.25 * segment * 3.0, (chamber, segment)
    laid = ready.Place(stage, place)
    swung = {name: ready.opened_leaf(laid, name, {"hinge": door["pivot"], "degrees": door["open"]}).centroid
             for name, door in doors.items()}
    assert swung["inner_door"][2] < 0.0 and swung["outer_hatch"][2] < 2.84, swung  # to the porch; into the chamber
    blocks_lock(tmp_path)


def blocks_lock(tmp_path):
    """An airlock built from blocks (a cell of walls, deck and roof, no dome shell: 2099 #164) is a chamber by its
    doors' marks (place_build.door): its inner plug door slides aside along its face, for the walkers and in the
    package, its outer door swings into the cell, and the cell's air is its hull's over the deck."""
    from score.stages.place_build import scene_package
    folder = tmp_path / "cell_lock"
    place_build.start(folder, "cell_lock", tmp_path / "concept.png")
    walls = [[x0, 0, -1.7, x1, 2.5, -0.5, "wall"] for x0, x1 in ((-2.2, -2.0), (2.0, 2.2))]
    walls += [[x0, 0, 0.5, x1, 2.5, 1.7, "wall"] for x0, x1 in ((-2.2, -2.0), (2.0, 2.2))]
    walls += [[x0, 2.1, -0.5, x1, 2.5, 0.5, "wall"] for x0, x1 in ((-2.2, -2.0), (2.0, 2.2))]
    walls += [[-2.0, 0, z0, 2.0, 2.5, z1, "wall"] for z0, z1 in ((-1.7, -1.5), (1.5, 1.7))]
    place_build.blocks(folder, "cell", [[-2.2, -0.1, -1.7, 2.2, 0.0, 1.7, "deck"], *walls,
                                        [-2.2, 2.5, -1.7, 2.2, 2.7, 1.7, "roof"]])
    place_build.blocks(folder, "plug", [[-2.15, 0.0, -0.5, -2.05, 2.1, 0.5, "door"]])
    place_build.blocks(folder, "hatch", [[2.05, 0.0, -0.5, 2.15, 2.1, 0.5, "door"]])
    stage, place = place_build.opened(folder)  # a mark of another type, as places laid before #148 carry
    stage.GetPrimAtPath(f"/{place}/Objects/plug").CreateAttribute("score:opens", Sdf.ValueTypeNames.Bool).Set(True)
    stage.GetRootLayer().Save()
    place_build.door(folder, "plug", opens=True, move="slide", lock="cell", side="inner")
    place_build.door(folder, "hatch", lock="cell", side="outer")
    try:
        place_build.door(folder, "hatch", side="outer")
        raise AssertionError("a door's side was taken with no chamber named")
    except place_build.Refused:
        pass
    scene = scene_package.write(folder, tmp_path / "cell_package")
    doors = {copy["name"]: copy["door"] for copy in scene["instances"] if "door" in copy}
    plug, hatch = doors["plug"], doors["hatch"]
    stage, place = place_build.opened(folder)
    laid = ready.Place(stage, place)
    [chamber] = scene["chambers"]
    assert (chamber["name"], chamber["inner"], chamber["outer"]) == ("cell", ["plug"], ["hatch"]), scene["chambers"]
    assert 4.0 * 3.0 * 2.5 < chamber["air_volume"] <= 4.4 * 3.4 * 2.7 + 1e-6, chamber
    assert (plug["lock"], plug["side"], hatch["lock"], hatch["side"]) == ("cell", "inner", "cell", "outer")
    assert plug["move"] == "slide" and plug["limits"] == [0.0, 1.0] and plug["opens"] is True, plug
    assert np.allclose(np.abs(plug["axis"]), [0.0, 0.0, 1.0]), plug
    slid = ready.doors_standing(laid)["plug"].bounds - laid.meshes["plug"].bounds
    assert np.allclose(slid, [np.asarray(plug["axis"]) * plug["open"]] * 2, atol=1e-6), slid
    into = ready.opened_leaf(laid, "hatch", {"hinge": hatch["pivot"], "degrees": hatch["open"]}).centroid
    assert hatch["move"] == "hinge" and into[0] < 2.05, (hatch, into)  # into the cell, never out into the vacuum
    walled = tmp_path / "wall_lock"  # the same cell, its doors naming one wall of it (the shiplock's hull_wall)
    place_build.start(walled, "wall_lock", tmp_path / "concept.png")
    place_build.blocks(walled, "back_wall", [[-2.0, 0, 1.5, 2.0, 2.5, 1.7, "wall"]])
    place_build.blocks(walled, "cell", [[-2.2, -0.1, -1.7, 2.2, 0.0, 1.7, "deck"], *walls[:-1],
                                        [-2.2, 2.5, -1.7, 2.2, 2.7, 1.7, "roof"]])
    place_build.blocks(walled, "plug", [[-2.15, 0.0, -0.5, -2.05, 2.1, 0.5, "door"]])
    place_build.blocks(walled, "hatch", [[2.05, 0.0, -0.5, 2.15, 2.1, 0.5, "door"]])
    place_build.door(walled, "plug", lock="back_wall", side="inner")
    place_build.door(walled, "hatch", lock="back_wall", side="outer")
    place_build.blocks(walled, "knob", [[1.0, 1.0, 1.0, 1.1, 1.1, 1.1, "knob"]], role="prop")
    place_build.blocks(walled, "couplet", [[30.0, 1.0, 1.0, 30.2, 2.5, 1.01, "paper"]], role="mount",
                       support="wall:cell")
    try:
        place_build.blocks(walled, "slab", [[0, 0, 0, 1, 1, 1, "slab"]], role="door")
        raise AssertionError("blocks laid as a door")
    except place_build.Refused:
        pass
    stage, place = place_build.opened(walled)
    laid_walled = ready.Place(stage, place)
    middle, axes, _ = ready.frame_of(laid_walled, "plug")
    assert laid_walled.roles["knob"] == "prop" and ready.inward(laid_walled, middle, axes[2]) is not None
    assert laid_walled.roles["couplet"] == "mount" and \
        laid_walled.prims["couplet"].GetAttribute("score:support").Get() == "wall:cell"
    _, chambers = scene_package.locks_of(laid_walled)
    assert [(chamber["name"], chamber["inner"], chamber["outer"]) for chamber in chambers] == \
        [("back_wall", ["plug"], ["hatch"])] and 3.0 * 2.0 * 2.0 < chambers[0]["air_volume"] < 4.4 * 3.4 * 2.7, chambers
    hollowed(walled)


def hollowed(folder):
    """A street's block turned a quarter (its shop's face on -z) hollowed where the area seats a neighbour place in it
    (2099's prologue: the walker began inside the street's block wall_l1): its boxes cut to what stands outside the
    region, in their parts, pose and role; the shop's table and lamp, the rack on the gone face and the wash on that
    rack taken out with it, the door leaf, the sign on the face and a neighbouring block reaching into the region
    left kept."""
    place_build.blocks(folder, "block", [[0, 0, 0, 4, 3, 6, "wall"], [-0.3, 0, 0, 0, 3, 6, "base"]], at=(40, 0, 0),
                       turn=(0, -90, 0))
    place_build.blocks(folder, "table", [[36.8, 0, 0.8, 37.2, 0.8, 1.2, "top"]], role="prop")
    place_build.blocks(folder, "rack", [[36.7, 1.0, -0.9, 37.3, 1.2, -0.3, "rack"]], role="mount",
                       support="wall:block")
    place_build.blocks(folder, "wash", [[36.8, 0.4, -1.3, 37.2, 1.0, -1.05, "cloth"]], role="mount",
                       support="wall:rack")
    place_build.blocks(folder, "sign", [[34.5, 1.0, -0.4, 35.5, 1.4, -0.3, "sign"]], role="mount",
                       support="wall:block")
    place_build.blocks(folder, "gate", [[36.9, 0.0, -0.2, 37.6, 1.9, -0.15, "leaf"]], role="prop")
    place_build.door(folder, "gate", opens=True)
    place_build.light(folder, "shop_lamp", at=(37.0, 1.5, 1.0), watts=10)
    place_build.blocks(folder, "next_block", [[37.5, 0, -0.9, 37.9, 2.6, -0.5, "wall"]])
    region = [36.0, -1.0, -1.0, 38.0, 2.0, 2.0]
    made = place_build.hollow(folder, "block", [region])
    stage, place = place_build.opened(folder)
    prim = stage.GetPrimAtPath(f"/{place}/Objects/block")
    boxes = place_build.laid_boxes(stage, prim)
    world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    corners = [np.array([[x, y, z, 1.0] for x in box[0::3][:2] for y in box[1::3][:2] for z in box[2::3][:2]]) @ world
               for box in boxes]
    inside = [corner for corner in corners if np.all(corner[:, :3].min(axis=0) < np.array(region[3:]) - 1e-4)
              and np.all(corner[:, :3].max(axis=0) > np.array(region[:3]) + 1e-4)]
    volume = sum(np.prod(np.array(box[3:6]) - box[:3]) for box in boxes)
    assert not inside and np.isclose(volume, 4 * 3 * 6 + 0.3 * 3 * 6 - 2 * 2 * 2 - 2 * 2 * 0.3, atol=1e-3), boxes
    assert {box[6] for box in boxes} == {"wall", "base"} and sorted(made["taken_out"]) == ["rack", "shop_lamp", "table",
                                                                                           "wash"], made
    assert place_build.pose_of(prim)[1] == [0.0, -90.0, 0.0] and prim.GetAttribute("score:role").Get() == "structure"
    assert all(stage.GetPrimAtPath(f"/{place}/Objects/{name}") for name in ("sign", "gate", "next_block")), made
