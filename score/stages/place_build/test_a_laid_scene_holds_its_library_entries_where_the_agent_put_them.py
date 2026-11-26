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
made geometry as untextured GLBs a mesh a part, a library piece's laid geometry with its texture coordinates (a kit
card's palette swatch replaced by its box's, so a decal's page spans its face), each copy's parts' looks, its check sound and refusing a stale digest,
a withdrawn entry, a changed made file and a part with no look) and
the laid scene packaged for an engine (score.scene v1, package.py's check sound) with every copy filling its laid box,
copies in one surface one object, its texture caps the game's (a film package's raised, the game's set back after), a glTF model laid unchanged its own library glTF, its looks as PBR (a palette
recipe baked into its own maps, on a ground one seamless tile; glass as transmission), its colliders from the
physics check's roles and the place's environment (its night, sun and grade), its bake run a few maps of one object at
a time and a stopped bake resumed from the maps it finished, a changed object's maps baked again. A wall the camera cuts (place.json `cut`) is
no solid to the film's camera and still one to the walkers, cut in the concept's view and a view made a cut view while
an outside view sees it standing, and a cut stair core's front wall is written to its own file. A still draws the place
without the walkers' layer. A Moon place's physical sky (sky-at) holds what overhead.py says is overhead at its
site and time (the light stage's own gate finds no fault), a sky laid before cleared, each body in its library face
or named missing when the library holds none, black under the airless sky at the brightest light's exposure; a Mars
site's sun reddened through its dust under its day dome, whose light is its ambient light; a body with air the dust
table lacks is refused.

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
- gltf.moving_node: never finding one (None) -> the made door is joined into the body's geo, no hinge to read (#177);
  gltf.in_part: the points left in the scene's frame -> the door's slab stands its pivot's offset off
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
- cockpit_kit.near_hole: THROUGH dropped -> a porthole's axis, run on across the room, cuts its hole in the far
  wall too
- cockpit_kit.lining_depth: a fade measured straight from the hole's middle again -> a cushion of the lining swells
  through a wide hole's inner flange at its sides, where the cone curves away
- place_build.kit: a part with no look left in its placeholder -> the toggle laid with no look for its lever is not
  refused
- cockpit_kit.course_seams: a panelled lining's courses started at random again -> its wall panels' joints no longer
  line up course over course from `panel_from`
- cockpit_kit.wheel: the rim's ends laid on one face again -> the valve handwheel is no closed solid
- cockpit_kit.vent: a louvre laid as one face, not a slat -> the closed panel's vent grille is no closed solid
- cockpit_kit.wall_screws: a hole's clearance dropped -> a wall panel's screw stands on the porthole's flange
- launch_kit.ship: the barrel and the nose turned as two solids (the barrel's top left open) -> the ship's welded
  mesh has an edge used three times (no closed solid)
- launch_kit.ship: the aft skirt left off -> the ship's lowest points are its engine bells', not the skirt it stands on
- launch_kit.lattice: a brace drawn as a stair of boxes -> a brace's points stray from the straight line between its ends
- launch_kit.ship: `ring` 0 read as the default 2 m of seams -> the seamless ship has a seam part
- launch_kit.ship_trim: a panel line laid on a flap's line, or a trim not sunk under the hull's face -> the ship's trim
  stands on its flaps or floats off its hull; its panel lines run on through the seams, or a course's lines stand
  where the course below's do -> the ship's panel lines read as one grid
- launch_kit.ferry: its wake laid under the waterline -> the ferry's wake is not on the water
- launch_kit.water: shaded smooth -> the harbour's top normals lean off straight up
- launch_kit.door_wall: the reveal's sides left off -> the wall with a round doorway is no closed solid
- launch_kit.coast: its sides left off -> the coast is no closed solid; its bottom wound up -> its edges are not
  walked once each way
- launch_kit.coast_heights: the sites unread -> the coast's launch site stands off its 3 m; the sea bed left at the
  waterline -> the coast's sea bed 60 m out is not 8 m down; the hills left flat -> its land rises no higher than
  its berm
- launch_kit.coast_dressing: a road's slab wound inward or left open -> a coast road is no closed solid facing out;
  laid at its ground's height less its slab -> a coast road is under its ground; the sites unread -> the coast's night
  dressing stands on its launch site
- launch_kit.coast_trees: a crown left open or wound inward -> the coast's woods are no closed solids facing out; laid
  at its ground's height -> a coast tree floats; the sites unread -> a coast tree stands on its launch site
- launch_kit.coast_palms: a frond or trunk left open or wound inward -> a coast frond (palm) is no closed solid facing
  out; the sites unread -> a coast palm stands on its launch site; a clump of undergrowth or an evergreen left open or wound
  inward -> a coast shrub (tree_spire) is no closed solid facing out; undergrowth laid on its site -> a coast shrub
  stands on its launch site; the evergreens never grown -> the parts read palm, frond, shrub without tree_spire
- launch_kit.hatch_band: a hatch row's run laid as a whole ring -> the hatched ship's skin stands across its hatch
- launch_kit.hatched: the band laid on the hull with no gap -> the hatched ship's hull shares a face with its band
- launch_kit.door_wall: the rows' sill row left out of the doorway -> the wall's volume is a round doorway's short
- place_build.kit: a door wall's doorway not recorded -> place.json holds no doorway arm_end_door to join at
- place_build.kit: the doorway left in the wall's own frame -> the recorded doorway's inward is not the turned +x
- place_build.remove: a removed door wall's doorway and join kept -> the pad's walkway still joins at a wall gone
- place_build.haze: `shape` dropped (always a box) -> the steam puff's shell reaches its box's corners
- place_build.shaft: the cone not turned onto its aim -> the beam's shell runs up, not toward its aim
- scene_package.hazes_of: the shape left off (every body a box) -> the puff packaged as a box, the beam with no apex
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
- place_build.airless: every body taken as airless -> a Mars site is laid under a black sky with no day dome
- place_build.sky_at: the dust not passed to the sky -> Mars's low sun shines white, not reddened through its dust
- place_build.sky_light: the dome's light left off the Environment -> Mars's ambient light is nought
- place_build.day_dome: the picture named as the light layer's (../assets) -> the dome's picture is not in the folder
- place_build.dusty_air: a body with air and no dust laid -> the Earth's site is laid with no refusal
- dome_shell.written: no placeholder bound to a part -> the written parts' bindings are empty
- dome_shell.placeholder: its shader left out -> the glass placeholder has no surface to draw (Cycles' black)
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
- stair_core.block: `ledges(holes)` left out -> a facade window has no sill proud of the facade under it
- stair_core.newelled: `inset` -> `0.0` at the well -> a flight's handrail stops short of the well's cross
  railing
- stair_core.railings: `newelled` left out -> the flights' handrails stop in mid-air at every turn
- stair_core.newelled: `turn_rail(x, floor)` -> the post's own flight's rail -> the well's two posts at a turn stand
  at two heights, the cross rail between them meeting neither cap
- stair_core.railings: a landing's railings at LANDING_RAIL -> its rail meets the flights' newel posts 8-12 cm
  under their caps
- place_build.rewritten: the open layer's content not taken (`write(path)` over it) -> a cut core laid again in one
  batch fails: USD makes no new layer where its front's is open
- dome_shell.written: `flat` ignored -> the stair core carries no faceVarying normals (it renders pillowed)
- render.views: FINAL_SIZE left off -> the final render keeps the concept's aspect
- render.libraries: the libs/ default dropped (SCORE_BLENDER_LIBS alone) -> a box without the variable starts a
  Blender that cannot find libSM (exit 127), and the failure names no fix
- place_build.layered: the layer mark left off -> the monitor's glow is no part and its screen takes no surface
- measure.lab: a and b read unsigned -> the concept's blue reads yellow (b over 0)
- measure.lightness: the render's L* read off the concept -> a white render beside a black concept reads as dark
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
- place_build.laid_reference: old_overs_dropped not called -> the swapped object keeps the old model's paint group
- place_build.copied_entry: a file already there always kept -> the rewritten draft's piece never reaches the place;
  every file copied again -> the place's edited piece.json is lost
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
- scene_package.rains_of: the laid rain's sizes not read (or place_build.rain not keeping them) -> the package has no rain to fall
- ground_tracks.rut_rows: LIFT left off -> the ruts' floor sinks into the ground
- place_build.remove: Effects not looked in -> the removed ruts stay laid
- place_build.usd_file: an effect's `usd` root unread -> the wisp lays its clip.usdc, not its emitter
- place_build.usd_file: a model's `usd` root unread (ROOTED_KINDS the effect alone) -> the adopted crate lays its
  base payload, not its root
- place_build.layered: a layer taken from any folder (the same-folder test dropped) -> the crate's payload
  sm_crate_01_geo is laid as its layer `geo`
- place_build.put: the record's usd.meters_per_unit unread (laid_reference given 1.0) -> the centimetre crate stands
  100 times too big; or place_build.posed's unit op left off -> it does after a snap; or scene_package.mass_of's
  `scale / place_build.units_of(prim)` dropped -> its mass is weighed by the centimetres too (1e-6 of it)
- place_build.put: the record's usd.up_axis unread (laid_reference given None), or place_build.posed's up-axis op
  left off -> the Z-up crate's own up lies along the scene's -x after the agent's quarter turn, not up
- library.replaced_end: the chain left unfollowed (`return address` at once) -> the retired crate is refused
  withdrawn, not laid as the adopted crate
- place_build.put: the replacement laid at the asked pose (in_footprint unread) -> the bench's answer has no footprint
- place_build.footprint_turn: always 0, or the fronts unread -> the long bench is not turned a quarter, or turned 90
  where the fronts say 270
- place_build.in_footprint: no shift (clear_shift unread) -> the bench lies 10 cm into the bin and 8 cm into the wall
- place_build.riders_of: the support compared to the bare name alone (`wall:<name>` uncounted) -> the plaque mounted
  on the bench is no rider and stays where it stood; place_build.set_back: a mount set back as one standing on it
  (its `wall:` branch dropped) -> it is not mounted back on the bench's face
- place_build.old_usd: every file of the old entry resolved (its texture too) -> the out-of-reach texture leaves
  the bench unmeasured, never turned into the old footprint; in_footprint without its `except
  library_files.LibraryUnreachable` -> the bench whose old entry is out of reach is never laid
- place_build.clear_shift: the first clear spot, not the nearest -> the bench moves a metre
- place_build.riders_of: the foot on the old top, or `score:support`, unread -> the cup blocks the bench's spot (it
  moves 40 cm), or the pen floats at 0.9 m
- place_build.set_back: unread -> the cup stays on the old top 5 cm into the new one
- place_build.put: an effect laid under Objects -> the wisp is a solid object with no role
- place_build.hold: the pose's rotations not written -> the walker's hips keep their clip's turn
- place_build.held_prop: the hold frame left out (the joint's transform alone) -> the stub sits on the hips, not
  0.1 m along their turned x
- place_build.held_prop: the turn decomposed X, Y, Z (not rotateXYZ's Z, Y, X reversed) -> the stub's up is off
- place_build.remove: place.json's cut left as it was -> a removed awning stays listed in the cut
- place_build.object_prim: Effects not looked in -> the ruts take no surface ("no object ruts")
- scene_package.copy_frame: every copy kept whole (no evenness test) -> a stretched copy fails the package check
- scene_package.taken_down: every picture kept at its own size -> a 64 texel map is packaged over HELD_TEXELS
- scene_package.capped: FILM_CAPS unread (`film` ignored) -> a film package holds the 64 map at the game's 32
- scene_package.capped: the caps not set back after -> the game's package holds the 64 map whole after a film's
- scene_package.packaged_capped: `textures` left out of scene.json -> the package names no caps it was written under
- scene_package.pictures_held: no picture held once (`by_bytes` unread) -> two of an object's images hold one picture
- scene_package.pictures_read_as: every map read as linear -> the base colour shares its picture with linear maps
- scene_package.held_image: unread in pbr (every map held whole) -> the dune's look holds its sand map at 64
- scene_package.write: every character made before any is written (character_objects, as before) -> the leader is
  written after the crowd's people are made (the square's 1,260 people held at once, past 14 GB)
- scene_package.gprim_pieces: the cube's own transform left out (identity) -> the crate's model misses its laid box
- scene_package.look_name: the look's own prim name -> the two steel walls are two objects
- scene_package.entry_glb: never reused (None) -> the cabinet is converted, not its library glTF
- scene_package.written_scene: an object's `library` left out (#143) -> the cabinet names no model/cabinet@1
- scene_package.shade_of: every object shaded (finished.picture_made unread) -> the monitor's maps ask the take's
  occlusion too; gltf_written not asking it (`asked["shade"]` dropped) -> the re-finished cup's maps ask none (#209)
- scene_package.finish_of: a decal's picture left out of the sha256 -> the cup's finish key is not its files' (#213)
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
- place_build.blocks: no rebind after laying -> the hollowed block's wall loses the look laid on it (a re-laid blocks
  file drops the old one's overs: the street's facades went white, 2099 2026-11-23)
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
- scene_package.run_needs: BAKE_MEMORY_GB whatever the maps (2026-11-24) -> an 8192 map's run held to 6 GB (the
  street's film bake killed at its first); its card BAKE_CARD_GB whatever the maps -> an 8192 map's run on 4 GB
- render.queued: `card_gb` and `memory_gb` ignored -> a bake run asks the queue for render.CARD_GB and no memory
- render.queued: the scope's cap MEMORY_GB whatever the job asks -> a 12 GB job's scope holds 8 GB (#159: the cart
  killed); OOMPolicy=continue left out -> a Blender killed past its cap exits 124, read as past its time
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
- skinned.lived: unread (plays left on the still pose) -> a held character plays `Held`, standing still in the game;
  skinned.taken_from: no sample matched -> the character held before its pose named its clip stays still;
  skinned.between_keys: only the keys tried -> the character held between two keys stays still;
  skinned.lived: ON_THE_SPOT unread -> the character held mid-stride treads `walking` on the spot
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
- pieces.engine_source: the laid USD's stem not matched -> a take of two glTFs names neither; the re-finished parts
  left unread -> the cup, cut into paint0, names a glTF that holds no such part
- pieces.sourced: no mesh written for an entry without a glTF -> the USD-only box piece has no meshes/box_piece.glb
- pieces.same_look: two looks of one part told apart by their prims alone -> the SimReady kit's two doors, each
  carrying its own copy of one material, refuse its piece list (#156)
- place_build.decal_read: a decal surface laid as a recipe -> the panel's page surface asks for a colour, or wears
  none of its page (2099 #161, the flat's blank white calendar)
- place_build.tinted: a decal's colour multiplied into its page -> the red paper's page has its ink tinted and no
  paper under it (2099 #161, the flat's poster)
- pieces.paged: a library mesh written without texture coordinates, or a kit card's swatch kept -> the card's page
  is one point and a SimReady model's maps read nothing (2099 #161, the flat's calendar and stove)
- pieces.own_look: a look bound inside the object taken for its own whatever it names -> the kit's door in a library
  surface is its own bake, and the engine draws the materialless mesh white (2099 #161, the flat's wardrobe)
- pieces.pictures_apart: the picture's view kept in the buffer, or the accessors' views not renumbered -> the
  character's GLB still holds its picture, or its keys read the picture's bytes; its picture kept at its own size
  (taken_down unread) -> the 64 texel picture is set apart at 64, over the game's 32
- pieces.held_pictures: every library picture left as the library holds it -> the dune's 62 texel sand map is named
  over the game's 32 with no held copy
- package.picture_problems: a held picture's hash unread -> a held sand changed passes; the exposure unread -> a
  piece list exposed at 0 passes
- scene_package.mass_of: the asset's authored mass left unread (usd_physics.authored_mass skipped) -> the adopted
  prop weighs its record's 3 kg, not its asset's 1.5496 kg times its scale cubed (#155)
- scene_package.metal_rough: the texture output read left off (`channel(found[0], "r")`) -> the adopted look's
  roughness and metal are its ORM map's occlusion (red), not its green and blue (#155)
- scene_package.gprims: its walk without Usd.TraverseInstanceProxies() -> the adopted prop whose mesh stands under an
  instanceable prim (a SimReady model's) draws nothing in its package (#155)
- scene_package.animated: its walk without Usd.TraverseInstanceProxies() -> the fan turning inside its instance reads
  still (#155)
- place_build.ground_points: its walk without Usd.TraverseInstanceProxies() -> the adopted ground laid under an
  instanceable prim reads no ground (#155)
"""
import hashlib
import io
import json
import math
import pathlib

import trimesh

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, UsdSkel, Vt

from score.stages import place_build
from score.stages.place_build import cockpit_kit, film, measure, ready, relief, render, review, stair_core


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
    entry("surface", "page", {"surface.json": ("record", json.dumps({"recipe": "decal", "maps": {"decal": "decal.png"}})),
                              "decal.png": ("texture", "a page")})
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
    for kind, entry_id, written in (("model", "sm_crate", {"usd": {"root": "simready_usd/sm_crate_01.usda",
                                                                              "meters_per_unit": 0.01,
                                                                              "up_axis": "Z"}}),
                                    ("model", "old_crate", {"state": "withdrawn", "replaced_by": "model/old_box@1"}),
                                    ("model", "old_box", {"state": "withdrawn", "replaced_by": "model/sm_crate@1"}),
                                    ("model", "gone", {"state": "withdrawn", "replaced_by": "model/gone_too@1"}),
                                    ("model", "gone_too", {"state": "withdrawn"}),
                                    ("surface", "old_steel", {"state": "withdrawn", "replaced_by": "surface/steel@1"})):
        if kind != "model" or entry_id != "sm_crate":
            entry(kind, entry_id, {})
        path = root / "entries" / kind / entry_id / "1" / "entry.json"
        path.write_text(json.dumps(dict(json.loads(path.read_text()), **written)))
    for entry_id, size, written in (("old_bench", (1.2, 0.75, 0.6), {"state": "withdrawn",
                                                                     "replaced_by": "model/long_bench@1"}),
                                     ("long_bench", (0.8, 0.8, 1.6), {})):  # its long side across the old one's
        bench = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(bench, UsdGeom.Tokens.y)
        bench.SetDefaultPrim(UsdGeom.Xform.Define(bench, "/bench").GetPrim())
        top = UsdGeom.Cube.Define(bench, "/bench/geo")
        top.AddTranslateOp().Set(Gf.Vec3d(0.0, size[1] / 2, 0.0))
        top.AddScaleOp().Set(Gf.Vec3f(*(side / 2 for side in size)))
        textured = {"wood.png": ("texture", None)} if entry_id == "old_bench" else {}  # a box needs no texture
        entry("model", entry_id, {"model.usda": ("usd", bench.GetRootLayer().ExportToString()), **textured})
        path = root / "entries" / "model" / entry_id / "1" / "entry.json"
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
    # a draft rewritten in place reaches a place laying it again; a copy the place changed is kept (#156)
    library_piece = files / "kit/box_piece@1/piece.usda"
    library_piece.write_text(library_piece.read_text() + "\n# rewritten in place\n")
    (files / "kit/box_piece@1/piece.json").write_text('{"rewritten": true}')
    (folder / "assets/kit/box_piece/1/piece.json").write_text('{"edited": true}')
    place_build.put(folder, "dune", "kit/box_piece", at=(6, 0, 0))
    assert (folder / "assets/kit/box_piece/1/piece.usda").read_text().endswith("# rewritten in place\n")
    assert json.loads((folder / "assets/kit/box_piece/1/piece.json").read_text()) == {"edited": True}
    # another model laid on a taken name drops the old one's own overs (its paint groups), keeps nothing stale (#156)
    place_build.put(folder, "swapped", "kit/box_piece", at=(50, 0, 50))
    swapped = Sdf.Layer.FindOrOpen(str(folder / "scene.usda"))
    Sdf.CreatePrimInLayer(swapped, "/yard/Objects/swapped/geo/paint0")
    swapped.Save()
    del swapped
    place_build.put(folder, "swapped", "model/cabinet", at=(50, 0, 50))
    assert not Sdf.Layer.FindOrOpen(str(folder / "scene.usda")).GetPrimAtPath("/yard/Objects/swapped").nameChildren
    place_build.remove(folder, "swapped")
    place_build.surface(folder, "dune", "surface/sand", colour="#ff8000")
    place_build.light(folder, "bulb", at=(0, 2.5, 0), watts=100)
    place_build.light(folder, "flood", at=(0, 8.0, 0), watts=200, aim=(0, 0, 6.0), angle=20.0)
    with pytest.raises(place_build.Refused, match="both --aim and --angle"):
        place_build.light(folder, "half", at=(0, 8.0, 0), watts=200, aim=(0, 0, 6.0))
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
    place_build.surface(folder, "panel", "surface/page")  # a decal: its page read as the colour, no --colour asked
    paged = Usd.Stage.Open(str(folder / "scene.usda"))
    page_source = UsdShade.Shader.Get(paged, "/yard/Looks/panel/surface").GetInput("diffuseColor").GetConnectedSources()[0]
    page_file = UsdShade.Shader(page_source[0].source.GetPrim()).GetInput("file").Get().path if page_source else None
    del paged
    place_build.surface(folder, "panel", "surface/page", colour="#ff0000")  # a page on red paper
    papered = Usd.Stage.Open(str(folder / "scene.usda"))
    paper = UsdShade.Shader.Get(papered, "/yard/Looks/panel/surface").GetInput("diffuseColor")
    page_scale = UsdShade.Shader.Get(papered, "/yard/Looks/panel/decal").GetInput("scale")
    paper_colour, page_tinted = tuple(paper.Get()), bool(page_scale and page_scale.Get() is not None)
    del papered
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
    assert page_file and page_file.endswith("page/1/decal.png"), page_file  # the decal's page is its colour
    assert np.allclose(paper_colour, (1.0, 0.0, 0.0)) and not page_tinted  # its ink kept, laid on paper of the colour
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
    from score.stages.place_build import dome_shell  # each part bound to its own placeholder: any reader splits them
    written = Usd.Stage.Open(str(dome_shell.written(tmp_path / "parts.usda", "parts", [
        ("glass", ([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [[0, 1, 2]])), ("rib", ([(0, 0, 1), (1, 0, 1), (0, 1, 1)], [[0, 1, 2]]))])))
    assert {subset.GetPrim().GetName(): UsdShade.MaterialBindingAPI(subset.GetPrim()).GetDirectBinding().GetMaterialPath().name
            for subset in UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Mesh(written.GetPrimAtPath("/parts/geo")))} == \
        {"glass": "glass", "rib": "rib"}
    grey = UsdShade.Material(written.GetPrimAtPath("/parts/Looks/glass"))  # drawn grey by any reader, marked as no finish
    assert grey.GetPrim().GetAttribute(dome_shell.PLACEHOLDER).Get() and tuple(
        grey.ComputeSurfaceSource()[0].GetInput("diffuseColor").Get()) == pytest.approx(dome_shell.PLACEHOLDER_GREY)
    assert sorted(next(item for item in shown["objects"] if item["name"] == "tunnel")["parts"]) == ["deck", "ribs", "shell", "wall"]
    assert np.allclose(boxes["tunnel"], [[18.38, -0.12, 0.0], [21.62, 3.12, 4.0]], atol=0.01)
    assert np.allclose(boxes["dome"], [[-5.18, 0.0, -5.18], [5.18, 5.1, 5.18]], atol=0.02)  # its plinth
    assert shown["lights"] == [{"name": "bulb", "at": [0.0, 2.5, 0.0], "watts": 100.0},
                              {"name": "flood", "at": [0.0, 8.0, 0.0], "watts": 200.0},
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
    sill = stair_core.STOREY + stair_core.WINDOW[1] - stair_core.LEDGE_GAP  # the first storey's windows' sills
    proud = across[np.isclose(across[:, 0, 2], -stair_core.FACADE - stair_core.LEDGE[2], atol=1e-5)
                   & np.isclose(across[:, 1, 2], -stair_core.FACADE - stair_core.LEDGE[2], atol=1e-5)
                   & np.isclose(across[:, 1, 1], sill, atol=1e-5)]  # each sill's front face
    assert len(proud) == len(stair_core.WINDOWS), proud  # each facade window a sill proud of the facade under it
    place_build.start(tmp_path / "well", "well", tmp_path / "concept.png")  # a cut core laid again in one batch
    relaid = place_build.batch(tmp_path / "well", [{"step": "stairs", "name": "core", "storeys": 1, "cut": True},
                                                   {"step": "stairs", "name": "core", "storeys": 1, "cut": True,
                                                    "street": True}])
    assert relaid[1]["street"] and "core_street" in place_build.record_of(tmp_path / "well")["doorways"], relaid
    stair_core.front_alone(tmp_path / "front.usda", 1)  # the wall a cut core leaves to its own object
    front_stage = Usd.Stage.Open(str(tmp_path / "front.usda"))
    front = np.asarray(UsdGeom.Mesh(front_stage.GetPrimAtPath("/stair_front/geo")).GetPointsAttr().Get())
    assert ((front[:, 0] > 0) & (front[:, 0] < stair_core.LONG) & (front[:, 2] < 0) & (front[:, 1] > 0.5)).any()
    newels = [np.asarray(points) for part, (points, _) in stair_core.railings(1) if part == "balusters"
              and np.allclose(np.ptp(np.asarray(points)[:, [0, 2]], axis=0), stair_core.NEWEL)]
    inset, landing, head = stair_core.RAIL_INSET, stair_core.LANDING, stair_core.LANDING + stair_core.RUN
    joints = [(landing, 0.0, inset), (landing - inset, stair_core.STOREY, stair_core.DEEP - stair_core.WIDE + inset),
              (head, stair_core.STOREY / 2, inset), (head + inset, stair_core.STOREY / 2, stair_core.WIDE - inset)]
    met = [any(post[:, 0].min() <= x <= post[:, 0].max() and post[:, 2].min() <= z <= post[:, 2].max()
               and post[:, 1].min() <= floor + 1e-6 and post[:, 1].max() >= floor + stair_core.LANDING_RAIL
               for post in newels) for x, floor, z in joints]
    assert all(met), met  # every landing's railing meets its flight's handrail at a newel post
    tops = {}
    for post in newels:
        tops.setdefault((round(post[:, 0].mean(), 3), round(post[:, 1].min(), 3)), set()).add(round(post[:, 1].max(), 4))
    assert all(len(level) == 1 for level in tops.values()), tops  # the well's two posts at one turn stand level
    rails = [rail for part, (points, _) in stair_core.railings(1) if part == "handrail"
             for rail in [np.asarray(points)] if np.ptp(rail[:, 1]) <= stair_core.RAIL_SIZE[1] + 1e-6]  # landings'
    short = [(round(post[:, 0].mean(), 3), round(post[:, 1].max() - rail[near][:, 1].max(), 3))
             for post in newels for rail in rails
             for near in [(np.abs(rail[:, 0] - post[:, 0].mean()) <= stair_core.NEWEL)
                          & (np.abs(rail[:, 2] - post[:, 2].mean()) <= stair_core.NEWEL)
                          & (rail[:, 1] >= post[:, 1].min()) & (rail[:, 1] <= post[:, 1].max() + 0.2)] if near.any()
             and post[:, 1].max() - rail[near][:, 1].max() > stair_core.RAIL_SIZE[1] / 2 + 0.03]
    assert not short, short  # every landing's handrail meeting a newel post reaches its cap
    listed_views = render.views(place_build.record_of(folder), 80, ["inside"])["views"]
    assert [view["name"] for view in listed_views] == ["concept", "inside"] and listed_views[1]["look_only"]
    assert (compared["layout_iou"], compared["objects"][0]["covered"], compared["colour"]["mean"]) == (0.5, 0.5, 0.0)
    assert measure.lab(Image.open(folder / "concept.png").convert("RGB"))[0, 0, 2] < -40
    assert measure.lightness(Image.new("RGB", (4, 4)), Image.new("RGB", (4, 4), (255, 255, 255)),
                             np.ones((4, 4), dtype=bool)) == {"concept": 0.0, "render": 100.0}
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
    kitted(tmp_path)
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
    hinged_converted(tmp_path / "hinged")
    footprinted(tmp_path)


def kitted(tmp_path):
    """A cockpit's code-built pieces (cockpit_kit, `kit`): two walls of the capsule's quilted lining, a porthole's
    hole cut in the near one alone (its axis runs on across the room to the far one, which stays whole), each wall
    one closed body in its looks; a panel's label in modelled letters; a piece with a part given no look refused by
    that part."""
    folder = tmp_path / "pod"
    place_build.start(folder, "pod", tmp_path / "concept.png")
    place_build.palette(folder, tmp_path / "palette.json", wear=0.4, dirt=0.3)
    looks = {"cushion": "palette/hull_paint", "seam": "palette/hull_paint", "back": "palette/hull_paint"}
    hole = [0.0, 1.2, 0.25]
    laid = {name: place_build.kit(folder, name, "lining", {"holes": [hole], "sector": sector, "cell": 0.05,
                                                            "rows": 0.05}, role="structure", looks=looks)
            for name, sector in (("near", [-30, 30]), ("far", [150, 210]))}
    panel = place_build.kit(folder, "plate", "panel", {"wide": 0.3, "high": 0.2, "label": "AB"}, at=(0, 1, -0.2),
                            looks={part: "palette/hull_paint" for part in ("plate", "bezel", "label", "ink", "bolt")})
    with pytest.raises(place_build.Refused, match="lever"):
        place_build.kit(folder, "bare", "toggle", looks={"metal": "palette/hull_paint"})
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    cone = cockpit_kit.Cone()
    middle, axis = cone.at(0.0, hole[1]), cone.inward(0.0)
    walls, off_axis = {}, {}
    for name in laid:
        geo = UsdGeom.Mesh(stage.GetPrimAtPath(f"/pod/Objects/{name}/geo"))
        points = np.asarray(geo.GetPointsAttr().Get(), dtype=np.float64)
        faces = np.asarray(geo.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
        walls[name] = trimesh.Trimesh(points, faces, process=False).split(only_watertight=False)
        along = (points - middle) @ axis
        off_axis[name] = np.linalg.norm(points - middle - along[:, None] * axis, axis=1).min()
    assert laid["near"]["parts"] == ["back", "cushion", "seam"] and panel["parts"] == ["bezel", "bolt", "ink",
                                                                                         "label", "plate"], (laid, panel)
    assert all(len(bodies) == 1 and bodies[0].is_watertight and bodies[0].volume > 0 for bodies in walls.values())
    assert off_axis["near"] > hole[2] - 0.01 and off_axis["far"] < 0.05, off_axis  # the hole in the near wall only
    assert all(stage.GetPrimAtPath(f"/pod/Looks/near__{part}").GetAttribute("score:surface").Get()
               for part in ("cushion", "back"))
    assert stage.GetPrimAtPath("/pod/Objects/plate").GetAttribute("score:support").Get() is None
    hatch = {"at": [0.0, 1.0], "radius": 0.7, "wall": 0.04, "flange": 0.08}
    reach = hatch["radius"] + hatch["wall"] + hatch["flange"]
    hatched = cockpit_kit.lining(holes=[[0.0, 1.0, reach - 0.07]], fades=[[0.0, 1.0, reach + 0.01]],
                                 sector=[-70, 70], cell=0.03, rows=0.03)
    face_points = np.vstack([piece[1][np.unique(piece[2])] for piece in hatched if piece[0] == "cushion"])
    along = (face_points - cone.at(0.0, 1.0)) @ cone.inward(0.0)
    under = cockpit_kit.off_axis(cone, face_points, 0.0, 1.0) < reach
    flange_top = (cone.onto(face_points, cone.inward(0.0), cone.sizes["gap"] + cone.sizes["lining"])
                  - cone.at(0.0, 1.0)) @ cone.inward(0.0) + 0.022
    assert under.any() and (along[under] < flange_top[under]).all(), (along - flange_top)[under].max()
    panelled = cockpit_kit.Cone(panels=15, panel_from=4.0)
    assert {start for start, _ in cockpit_kit.course_seams(panelled)} == {4.0 / 360.0}  # joints lined up
    screwed = cockpit_kit.Cone(panels=15, panel_from=4.0, panel_puff=0.006, quilted=[])
    heads = [found[1].mean(axis=0) for found in cockpit_kit.wall_screws(
        holes=[[16.0, 1.55, 0.2]], sector=[4.0, 28.0], panels=15, panel_from=4.0, panel_puff=0.006, quilted=[])]
    assert heads and min(cockpit_kit.off_axis(screwed, np.asarray(heads), 16.0, 1.55)) > 0.2 + 0.05
    for kind in ("wheel", "guarded_button", "ball", "breakers", "handrail", "annunciator", "talk_key", "cover", "vent"):
        built = cockpit_kit.KINDS[kind]()
        points, triangles = cockpit_kit.welded(np.vstack([found[1] for found in built]), np.vstack(
            [found[2] + sum(len(earlier[1]) for earlier in built[:number]) for number, found in enumerate(built)]))
        assert all(body.is_watertight for body in trimesh.Trimesh(points, triangles, process=False).split(
            only_watertight=False)), kind
    launched(folder)


def launched(folder):
    """A launch site's code-built pieces (launch_kit, `kit`): the ship one closed solid of welded parts standing on its
    skirt's foot (its engine bells clear above it), and a tower's braces each a straight bar between its ends."""
    from score.stages.place_build import cockpit_kit, launch_kit
    ship = place_build.kit(folder, "ship", "ship", {"radius": 1.0, "high": 12.0, "nose": 3.0, "ring": 2.0,
                                                    "segments": 24}, role="fixed",
                           looks={part: "palette/hull_paint" for part in ("hull", "seam", "tiles", "flap", "engine")})
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    geo = UsdGeom.Mesh(stage.GetPrimAtPath("/pod/Objects/ship/geo"))
    points = np.asarray(geo.GetPointsAttr().Get(), dtype=np.float64)
    faces = np.asarray(geo.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    welded, inverse = np.unique(np.round(points, 5), axis=0, return_inverse=True)
    edges = np.sort(inverse.reshape(-1)[faces][:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    _, uses = np.unique(edges, axis=0, return_counts=True)
    parts = {subset.GetPrim().GetName(): np.asarray(subset.GetIndicesAttr().Get())
             for subset in UsdGeom.Subset.GetAllGeomSubsets(geo)}
    lowest = {part: points[faces[found]].reshape(-1, 3)[:, 1].min() for part, found in parts.items()}
    assert ship["parts"] == ["engine", "flap", "hull", "seam", "tiles"], ship
    assert not (uses % 2).any(), "an edge of the ship is used an odd number of times"
    assert lowest["hull"] < 1e-6 < lowest["engine"], lowest
    braces = [piece for piece in launch_kit.lattice(wide=4.0, deep=4.0, high=6.0, bay=3.0, panels=1)
              if piece[0] == "brace" and len(piece[1]) > 12]  # the bars' sides, not their end caps
    for _, bar, _, _ in braces:
        ends = np.array([bar[:8].mean(axis=0), bar[-8:].mean(axis=0)])  # the middles of its end rings (8 a ring)
        along = (ends[1] - ends[0]) / np.linalg.norm(ends[1] - ends[0])
        off = bar - ends[0] - np.outer((bar - ends[0]) @ along, along)
        assert np.linalg.norm(off, axis=1).max() <= 0.12 + 1e-6, "a brace strays from its straight line"
    hatch = {"around": 30.0, "sill": 8.0, "low": 7.5, "high": 9.5, "thick": 0.05,
             "rows": [[0.0, -0.1, 0.1], [0.4, -0.3, 0.3], [0.8, -0.1, 0.1]]}
    hatched = [piece for piece in launch_kit.ship(radius=1.0, high=12.0, nose=3.0, ring=0.0, segments=24, hatch=hatch)
               if piece[0] == "hull"]
    points, triangles = cockpit_kit.welded(np.vstack([piece[1] for piece in hatched]), np.vstack(
        [piece[2] + sum(len(earlier[1]) for earlier in hatched[:number]) for number, piece in enumerate(hatched)]))
    edges = np.sort(triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    _, uses = np.unique(edges, axis=0, return_counts=True)
    assert not (uses % 2).any(), "an edge of the hatched ship is used an odd number of times"
    way = np.array([math.sin(math.radians(30.0)), 0.0, math.cos(math.radians(30.0))])
    across = np.cross([0.0, 1.0, 0.0], way)
    skin = points[np.linalg.norm(points[:, [0, 2]], axis=1) > 0.5]
    assert not ((np.abs(skin @ across) < 0.2) & (skin[:, 1] > 8.15) & (skin[:, 1] < 8.65) & (skin @ way > 0)).any(), \
        "the hatched ship's skin stands across its hatch"
    seamless = {piece[0] for piece in launch_kit.ship(radius=1.0, high=12.0, nose=3.0, ring=0.0, segments=24)}
    trim = launch_kit.ship_trim(radius=1.0, foot=0.4, shoulder=9.0, ring=2.0, stringers=8, raceway=90.0, segments=24,
                                bands=(2.0,), patch=(135.0, 5.0, 1.0, 0.5))
    assert sorted({piece[0] for piece in trim}) == ["marking", "raceway", "seam"], trim
    for part in ("marking", "raceway", "seam"):  # a turned ring is a piece a band, so each part's whole reach
        reach = np.linalg.norm(np.vstack([piece[1] for piece in trim if piece[0] == part])[:, [0, 2]], axis=1)
        assert reach.min() < 1.0 - 1e-6 < reach.max(), f"a {part} trim floats off the hull or stays inside it"
    lines = {}  # each panel line's angle round, by the course it stands in
    for part, points, _, _ in trim:
        if part == "seam" and np.ptp(points[:, 0]) < 0.5:  # a panel line, not a ring
            middle = points.mean(axis=0)
            angle = math.degrees(math.atan2(middle[2], middle[0]))
            assert launch_kit.TRIM_CLEAR - 1.0 < abs(angle) % 180.0 < 180.0 - launch_kit.TRIM_CLEAR + 1.0, \
                "a panel line stands on a flap's line"
            assert np.ptp(points[:, 1]) < 2.0, "a panel line runs on through a seam"
            lines.setdefault(round(float(middle[1]), 1), []).append(angle)
    courses = [lines[key] for key in sorted(lines)]
    assert len(courses) >= 3, lines
    for below, above in zip(courses, courses[1:]):
        assert min(abs((one - two + 180.0) % 360.0 - 180.0) for one in below for two in above) > 5.0, \
            "a course's panel lines stand where the course below's do: one grid"
    assert "seam" not in seamless, seamless
    ferry = launch_kit.ferry(long=20.0, wide=5.0, wake=30.0)
    wake = np.concatenate([piece[1] for piece in ferry if piece[0] == "wake"])
    assert wake[:, 1].min() >= 0.0 and wake[:, 0].max() < -10.0, (wake.min(axis=0), wake.max(axis=0))
    harbour = launch_kit.water(wide=1.0, deep=1.0, depth=0.5)  # small, so a lean from its chamfers would show
    points, triangles = cockpit_kit.welded(harbour[0][1], harbour[0][2])
    normals = cockpit_kit.corner_normals(points, triangles, harbour[0][3]).reshape(-1, 3, 3)
    tops = normals[np.all(np.abs(points[triangles][:, :, 1]) < 1e-9, axis=1)].reshape(-1, 3)
    assert len(tops) and tops[:, 1].min() > 1.0 - 1e-6, "the harbour's top leans"
    coast = launch_kit.coast(wide=400.0, deep=200.0, sea=100.0, rise=20.0, shore=10.0, cell=5.0,
                             sites=[[0.0, -100.0, 20.0, 3.0]])  # land, a shore, the sea bed, a launch site levelled
    assert [piece[0] for piece in coast] == ["land", "shore"], coast
    points, triangles = cockpit_kit.welded(coast[0][1], np.vstack([coast[0][2], coast[1][2]]))
    edges = triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)  # each walked once each way: closed, wound alike
    _, uses = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    corners = points[triangles]
    assert (uses == 2).all() and len(np.unique(edges, axis=0)) == len(edges) and np.einsum("ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum() > 0, \
        "the coast is no closed solid facing out"
    top = points[points[:, 1] > points[:, 1].min() + 1.0]
    land = coast[0][1][np.unique(coast[0][2])]
    site = top[np.hypot(top[:, 0], top[:, 2] + 100.0) < 15.0]
    assert np.allclose(site[:, 1], 3.0) and top[top[:, 2] > 60.0][:, 1].max() < -8.0 + 1e-6, (site, top.max(axis=0))
    assert land[:, 1].max() > 2.5 + 10.0 and land[:, 1].min() > 0.0, (land.min(axis=0), land.max(axis=0))  # above the sea
    dressed = launch_kit.coast(wide=400.0, deep=200.0, sea=100.0, rise=20.0, shore=10.0, cell=5.0,
                               sites=[[0.0, -100.0, 20.0, 3.0]], scrub=0.999, roads=2, houses=6)
    found = {part: [each for each in dressed if each[0] == part] for part in {each[0] for each in dressed}}
    assert {"scrub", "road", "post", "lamp", "house", "window"} <= set(found), sorted(found)
    ground = launch_kit.coast_ground(400.0, 200.0, 100.0, 20.0, 10.0, 2.5, 8.0, [[0.0, -100.0, 20.0, 3.0]], 0)
    for _, road_points, road_triangles, _ in found["road"]:
        rails = road_points.reshape(4, -1, 3)
        middle = (rails[0] + rails[1]) / 2  # the road's top along its middle
        assert (middle[:, 1] > ground(middle[:, 0], middle[:, 2])[0]).all(), "a coast road is under its ground"
        road_points, road_triangles = cockpit_kit.welded(road_points, road_triangles)
        corners = road_points[road_triangles]
        edges = road_triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
        assert len(np.unique(edges, axis=0)) == len(edges) and np.einsum(
            "ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum() > 0, "a coast road is no closed solid facing out"
    lit = np.vstack([each[1] for part in ("lamp", "house", "window") for each in found[part]])
    assert np.hypot(lit[:, 0], lit[:, 2] + 100.0).min() > 20.0, "the coast's night dressing stands on its launch site"
    _, wood_points, wood_triangles, _ = launch_kit.coast_trees(400.0, 200.0, 100.0, 20.0, 10.0, 2.5, 8.0,
                                                               [[0.0, -100.0, 20.0, 3.0]], 0, 40, 2)[0]
    wood_points, wood_triangles = cockpit_kit.welded(wood_points, wood_triangles)
    edges = wood_triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    _, uses = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    corners = wood_points[wood_triangles]
    assert (uses == 2).all() and len(np.unique(edges, axis=0)) == len(edges) and np.einsum(
        "ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum() > 0, "the coast's woods are no closed solids facing out"
    feet = wood_points[wood_points[:, 1] < ground(wood_points[:, 0], wood_points[:, 2])[0] - 0.4]
    assert len(feet) >= 3 * 40 * 0.5, "a coast tree floats"
    assert np.hypot(wood_points[:, 0], wood_points[:, 2] + 100.0).min() > 30.0, "a coast tree stands on its launch site"
    growth = [*launch_kit.coast_palms(400.0, 200.0, 100.0, 20.0, 10.0, 2.5, 8.0, [[0.0, -100.0, 20.0, 3.0]], 0, 12),
              *launch_kit.coast_shrubs(400.0, 200.0, 100.0, 20.0, 10.0, 2.5, 8.0, [[0.0, -100.0, 20.0, 3.0]], 0, 30),
              *launch_kit.coast_trees(400.0, 200.0, 100.0, 20.0, 10.0, 2.5, 8.0, [[0.0, -100.0, 20.0, 3.0]], 0, 40, 2)[1:]]
    assert [each[0] for each in growth] == ["palm", "frond", "shrub", "tree_spire"], [each[0] for each in growth]
    for part, palm_points, palm_triangles, _ in growth:
        palm_points, palm_triangles = cockpit_kit.welded(palm_points, palm_triangles)
        edges = palm_triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
        _, uses = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
        corners = palm_points[palm_triangles]
        assert (uses == 2).all() and len(np.unique(edges, axis=0)) == len(edges) and np.einsum(
            "ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum() > 0, f"a coast {part} is no closed solid facing out"
        assert np.hypot(palm_points[:, 0], palm_points[:, 2] + 100.0).min() > 15.0, f"a coast {part} stands on its launch site"
    circle = [[0.6 + 0.6 * math.sin(angle), -0.6 * math.cos(angle) - 0.01, 0.6 * math.cos(angle) + 0.01]
              for angle in np.linspace(-math.pi / 2, math.pi / 2, 31)]
    _, points, triangles, _ = launch_kit.door_wall(2.4, 2.6, 0.1, circle)[0]
    points, triangles = cockpit_kit.welded(points, triangles)
    edges = np.sort(triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    _, uses = np.unique(edges, axis=0, return_counts=True)
    corners = points[triangles]
    volume = float(np.einsum("ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum()) / 6
    assert (uses == 2).all(), "the door wall is no closed solid"
    doorway = sum((low[2] - low[1] + top[2] - top[1]) / 2 * (top[0] - low[0]) for low, top in zip(circle, circle[1:]))
    assert abs(volume - (2.4 * 2.6 - doorway) * 0.1) < 1e-6, (volume, doorway)
    place_build.kit(folder, "arm_end", "door_wall", {"wide": 2.4, "high": 2.6, "thick": 0.1, "rows": circle},
                    at=(3.0, 1.0, -6.0), turn=(0.0, 90.0, 0.0), role="structure", looks={"frame": "palette/hull_paint"})
    door = place_build.record_of(folder)["doorways"]["arm_end_door"]
    assert np.allclose(door["middle"], [3.0, 1.0, -6.0]) and np.allclose(door["inward"], [1.0, 0.0, 0.0]), door
    assert (door["sill"], door["head"], door["of"]) == (1.0, 2.2, "arm_end") and abs(door["wide"] - 1.22) < 1e-3, door
    from score.stages.place_build import area
    area.join(folder, "arm_end_door", "capsule")
    place_build.remove(folder, "arm_end")
    left = place_build.record_of(folder)
    assert "arm_end_door" not in (left.get("doorways") or {}) and "arm_end_door" not in (left.get("joins") or {}), left


def adopted(folder):
    """An adopted asset (#155) as the package reads it: its prop's mass the one its asset authors (UsdPhysics' MassAPI
    on its mesh) times its scale cubed, over its entry's record; its look's UsdPreviewSurface as Blender's importer
    reads it, the ORM map's green its roughness and blue its metal (red, occlusion, unread, as Blender reads none),
    the normal map (scale 2, bias -1) as glTF holds one, unchanged; a prop and a ground whose mesh stands under an
    instanceable prim (a SimReady model's) are drawn and stood on, and a fan turning inside its instance moves."""
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
    plate = UsdGeom.Mesh.Define(stage, "/Prototypes/plate/geo")
    plate.CreatePointsAttr([(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)])
    plate.CreateFaceVertexCountsAttr([4])
    plate.CreateFaceVertexIndicesAttr([0, 3, 2, 1])
    for name in ("prop_2", "floor_2"):
        stage.DefinePrim(f"/p/Objects/{name}", "Xform")
        shared = stage.DefinePrim(f"/p/Objects/{name}/Geometry/plate", "Xform")
        shared.GetReferences().AddInternalReference("/Prototypes/plate")
        shared.SetInstanceable(True)
    stage.GetPrimAtPath("/p/Objects/floor_2").CreateAttribute("score:ground", Sdf.ValueTypeNames.Bool).Set(True)
    drawn = [str(prim.GetPath()) for prim in scene_package.gprims(stage.GetPrimAtPath("/p/Objects/prop_2"))]
    assert drawn == ["/p/Objects/prop_2/Geometry/plate/geo"], drawn
    points, triangles = place_build.ground_points(stage, "p")
    assert len(points) == 4 and len(triangles) == 2, (points, triangles)
    turning = UsdGeom.Xform.Define(stage, "/Prototypes/fan/blade").AddRotateYOp()
    turning.Set(0.0, 0.0)
    turning.Set(90.0, 24.0)
    fan = stage.DefinePrim("/p/Objects/fan_1/Geometry/fan", "Xform")
    fan.GetReferences().AddInternalReference("/Prototypes/fan")
    fan.SetInstanceable(True)
    assert scene_package.animated(stage.GetPrimAtPath("/p/Objects/fan_1"))
    assert not scene_package.animated(stage.GetPrimAtPath("/p/Objects/prop_2"))


def replaced(tmp_path):
    """A withdrawn model and surface that name their replacements laid as the end of the chain (#155): the retired
    crate, through a retired box, as the adopted crate laid by its record's usd root (its payloads beside it, one named
    like the root's layers, never laid as a layer), the retired steel as the steel; a chain ending withdrawn refused.
    The adopted crate is authored in centimetres: laid at the agent's scale 2 its unit scale (0.01) is its own op
    after his, so his scale reads back as 2 and its mass is weighed by 2 cubed alone, never by the centimetres; and
    authored Z-up, its up-axis turn is its own op after that, so its own up stands along the scene's up under his
    quarter turn about up, before and after a snap."""
    from score.stages.place_build import scene_package
    folder = tmp_path / "replaced"
    Image.new("RGB", (8, 8)).save(tmp_path / "replaced.png")
    place_build.start(folder, "depot", tmp_path / "replaced.png")
    laid = place_build.put(folder, "crate", "model/old_crate", turn=(0.0, 90.0, 0.0), scale=(2.0, 2.0, 2.0))
    worn = place_build.surface(folder, "crate", "surface/old_steel@1")
    assert (laid["address"], laid["usd"], laid.get("layers")) == (
        "model/sm_crate@1", "./assets/model/sm_crate/1/simready_usd/sm_crate_01.usda", None), laid
    assert worn["surface"] == "surface/steel@1", worn
    stage, _ = place_build.opened(folder)
    assert stage.GetPrimAtPath("/depot/Objects/crate/geo"), "the adopted crate's root references its base payload"
    crate = stage.GetPrimAtPath("/depot/Objects/crate")
    world = np.asarray(UsdGeom.Xformable(crate).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    assert place_build.pose_of(crate)[2] == [2.0, 2.0, 2.0] and np.allclose(np.linalg.norm(world[:3, :3], axis=1),
                                                                           0.02), world
    assert np.allclose(world[2, :3], [0.0, 0.02, 0.0], atol=1e-6), world  # the asset's +Z along the scene's +Y
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        UsdPhysics.MassAPI.Apply(stage.GetPrimAtPath("/depot/Objects/crate/geo")).CreateMassAttr(1.5496)
    assert scene_package.mass_of(folder, crate, 0.02) == round(1.5496 * 8, 4)
    place_build.snap(folder, "crate")  # posed again: the unit scale and the up-axis turn kept
    world = np.asarray(UsdGeom.Xformable(crate).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    assert np.allclose(np.linalg.norm(world[:3, :3], axis=1), 0.02) and np.allclose(
        world[2, :3], [0.0, 0.02, 0.0], atol=1e-6), world
    with pytest.raises(place_build.Refused, match="gone_too@1: withdrawn"):
        place_build.put(folder, "lost", "model/gone")


def fetching_no_texture(resolve):
    """library_files.resolve that cannot fetch a texture (a library out of reach for all but the USD)."""
    def resolved(name, folder=None):
        if not name.endswith(".usda"):
            raise place_build.library_files.LibraryUnreachable(f"{name}: out of reach")
        return resolve(name, folder)
    return resolved


def fetching_nothing_of(entry_id):
    """library_files.resolve that cannot fetch any file of `entry_id`."""
    resolve = place_build.library_files.resolve

    def resolved(name, folder=None):
        if f"/{entry_id}@" in name:
            raise place_build.library_files.LibraryUnreachable(f"{name}: out of reach")
        return resolve(name, folder)
    return resolved


def hinged_converted(folder):
    """A made model with a moving part (maker/parts.py's GLB, #177: a door node `door_01__hinge_yn` at its pivot
    holding its slab, laid from that pivot) converts with the door its own Xform at the pivot, its slab where it was,
    and the motion layer reads its hinge off it."""
    from score.stages.motion import from_design
    from score.stages.place_build import gltf
    folder.mkdir()
    scene = trimesh.Scene()
    scene.add_geometry(trimesh.creation.box((1, 1, 1)), node_name="body_0", geom_name="body_0")
    scene.graph.update(frame_to="door_01__hinge_yn", frame_from=scene.graph.base_frame,
                       matrix=trimesh.transformations.translation_matrix((-0.5, 0.0, 0.55)))
    door = trimesh.creation.box((1, 1, 0.1)).apply_translation((0.5, 0.0, 0.0))
    scene.add_geometry(door, node_name="door_01_0", geom_name="door_01_0", parent_node_name="door_01__hinge_yn")
    scene.export(str(folder / "made.glb"))
    stage = Usd.Stage.Open(str(gltf.converted(folder / "made.glb")))
    part = stage.GetPrimAtPath("/model/door_01__hinge_yn")
    pivot = UsdGeom.Xformable(part).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
    slab = UsdGeom.Imageable(stage.GetPrimAtPath("/model/door_01__hinge_yn/geo")).ComputeWorldBound(
        Usd.TimeCode.Default(), "default").ComputeAlignedRange()
    body = UsdGeom.Imageable(stage.GetPrimAtPath("/model/geo")).ComputeWorldBound(
        Usd.TimeCode.Default(), "default").ComputeAlignedRange()
    assert np.allclose(pivot, (-0.5, 0.0, 0.55)) and np.allclose(slab.GetMin(), (-0.5, -0.5, 0.5))
    assert np.allclose(slab.GetMax(), (0.5, 0.5, 0.6)) and np.allclose(body.GetMax(), (0.5, 0.5, 0.5))
    assert from_design.parts_of(stage, "/model") == [("/model/door_01__hinge_yn", "hinge", "y", -1)]


def footprinted(tmp_path):
    """A withdrawn bench (1.2 m along x, 0.6 deep, 0.75 high) laid again as its replacement (0.8 x 0.8 x 1.6, its long
    side along z) in its footprint (#155: the adopted desk turned across the old one's spot cut into the dome wall and
    a bin): turned a quarter so its long side lies along the old one's, its floor on the old one's, moved the least
    that keeps it clear of the wall behind (8 cm into it, centred) and the bin beside (10 cm), never minding the cup
    on the old top and the pen marked as on the bench, both set back on the new top, and the plaque mounted on it
    (`wall:bench`), mounted back on its face at its height; measured by the old entry's USD alone (its texture out of
    reach); an old entry whose USD is out of reach laid at the asked pose, saying so; between two walls narrower than
    it, refused naming both. A front both records give turns it to the old front, else the long-side rule."""
    from score.stages.place_build import ready as ready_check
    rows = (((1.2, 0.6), (0.8, 1.6), None, None, 90), ((1.2, 0.6), (1.6, 0.8), None, None, 0),
            ((1.2, 0.6), (0.8, 1.6), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), 270),
            ((1.2, 0.6), (0.8, 1.6), (0.0, 0.0, 1.0), None, 90), ((1.0, 1.0), (0.8, 1.6), None, None, 0))
    for old, new, old_front, new_front, quarter in rows:
        assert place_build.footprint_turn(np.array(old), np.array(new), None if old_front is None else np.array(
            old_front), None if new_front is None else np.array(new_front)) == quarter, (old, new, old_front)
    Image.new("RGB", (8, 8)).save(tmp_path / "bench.png")
    folder = tmp_path / "footprint"
    place_build.start(folder, "shop", tmp_path / "bench.png")
    place_build.put(folder, "wall", "kit/box_piece", at=(-2.0, 0.0, -0.82), scale=(4.0, 1.0, 1.0))
    place_build.put(folder, "bin", "kit/box_piece", at=(0.7, 0.0, -0.3), scale=(0.4, 0.5, 1.2))
    place_build.put(folder, "cup", "kit/box_piece", at=(-0.05, 0.75, -0.05), scale=(0.1, 0.05, 0.1))
    place_build.put(folder, "pen", "kit/box_piece", at=(0.3, 0.9, 0.0), scale=(0.1, 0.02, 0.1), support="bench")
    place_build.put(folder, "plaque", "kit/box_piece", at=(-0.3, 0.3, 0.6), scale=(0.2, 0.1, 0.04), role="mount",
                    support="wall:bench")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(place_build.library_files, "resolve", fetching_no_texture(place_build.library_files.resolve))
        laid = place_build.put(folder, "bench", "model/old_bench", at=(0.0, 0.0, 0.0))
    stage, _ = place_build.opened(folder)
    box = ready_check.solid_of(stage.GetPrimAtPath("/shop/Objects/bench")).bounds
    assert laid["address"] == "model/long_bench@1" and laid["footprint"]["turned"] == 90, laid
    assert np.ptp(box[:, 0]) > np.ptp(box[:, 2]) and abs(box[0][1]) < 1e-6, box  # long side along x, on the floor
    assert box[1][0] <= 0.7 + 0.015 and box[0][2] >= -0.32 - 0.015, box  # clear of the bin and the wall
    assert laid["footprint"]["moved"] <= np.hypot(0.085, 0.065) + 0.025, laid  # the least move that clears them
    for rider in ("cup", "pen"):
        foot = ready_check.solid_of(stage.GetPrimAtPath(f"/shop/Objects/{rider}")).bounds[0][1]
        assert abs(foot - 0.8) < ready_check.TOLERANCE and rider in laid["footprint"]["reset"], (rider, foot, laid)
    plaque = ready_check.solid_of(stage.GetPrimAtPath("/shop/Objects/plaque")).bounds
    assert "plaque" in laid["footprint"]["reset"] and abs(plaque[0][2] - box[1][2]) < ready_check.TOLERANCE and abs(
        plaque[0][1] - 0.3) < 1e-6, (plaque, box, laid)  # mounted back on the new bench's face at its height
    folder = tmp_path / "unreached"
    place_build.start(folder, "unreached", tmp_path / "bench.png")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(place_build.library_files, "resolve", fetching_nothing_of("old_bench"))
        laid = place_build.put(folder, "bench", "model/old_bench", at=(0.5, 0.0, 0.5))
    stage, _ = place_build.opened(folder)
    bench = stage.GetPrimAtPath("/unreached/Objects/bench")
    assert laid["address"] == "model/long_bench@1" and place_build.pose_of(bench)[0] == [0.5, 0.0, 0.5] and \
        "unmeasured" in laid["footprint"], laid  # the old entry unmeasurable: laid by the old pose rule, and said
    folder = tmp_path / "slot"
    place_build.start(folder, "slot", tmp_path / "bench.png")
    for name, x in (("wall_a", -1.6), ("wall_b", 0.6)):
        place_build.put(folder, name, "kit/box_piece", at=(x, 0.0, -3.0), scale=(1.0, 1.0, 12.0))
    with pytest.raises(place_build.Refused, match="would cut wall_a, wall_b"):
        place_build.put(folder, "bench", "model/old_bench")
    assert not place_build.opened(folder)[0].GetPrimAtPath("/slot/Objects/bench"), "a refused bench left laid"


def skied(tmp_path, root, files):
    """A Moon place's physical sky from its site and time: what overhead.py says is overhead (the light stage's
    gate, sky.faults, on the turned answer), Earth in its library face, Mars's withdrawn face named missing, the sky
    laid before cleared, black at the Sun's exposure; a Mars site under its dusty day dome, the Earth refused."""
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
    mars = tmp_path / "mars_place"
    place_build.start(mars, "camp", tmp_path / "moon.png")
    laid = place_build.sky_at(mars, on="mars", latitude=30.013, longitude=130.314, time="2099-10-01T16:00:00Z")
    stage = Usd.Stage.Open(str(mars / "scene.usda"))
    beam = stage.GetPrimAtPath("/camp/Lights/sky_sun").GetAttribute("inputs:color").Get()
    dome = stage.GetPrimAtPath("/camp/Sky/Dome")
    picture = stage.GetPrimAtPath("/camp/Sky/dome_look/picture").GetAttribute("inputs:file").Get()
    ambient = stage.GetPrimAtPath("/camp/Environment").GetAttribute("inputs:color").Get()
    assert laid["dome"] and beam is not None and beam[0] > beam[2] and min(laid["ambient lux"]) > 0.0, laid
    assert dome.GetAttribute("score:sky_strength").Get() > 0.0 and ambient[0] > ambient[2], ambient  # a butterscotch sky
    assert (mars / picture.path).is_file() and \
        str(dome.GetAttribute("score:from").Get()).endswith(place_build.DUSTY_ALGORITHM), picture
    with pytest.raises(place_build.Refused, match="no dusty air"):
        place_build.sky_at(mars, on="earth", latitude=52.0, longitude=4.0, time=when)


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
    place_build.haze(folder, "puff", [62.0, 1.0, 62.0], [2.0, 2.0, 2.0], "#ffffff", 0.2, shape="ellipsoid")
    place_build.shaft(folder, "beam", [60.0, 5.0, 60.0], [70.0, 5.0, 60.0], 10.0, 8.0, "#ffffff", 0.05)
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    shells = {name: np.concatenate([np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get()) for prim in
                                    Usd.PrimRange(stage.GetPrimAtPath(f"/yard/Haze/{name}")) if prim.IsA(UsdGeom.Mesh)])
              for name in ("puff", "beam")}
    assert np.linalg.norm(shells["puff"] - [62.0, 1.0, 62.0], axis=1).max() <= 1.0 + 1e-4, "the puff is no ellipsoid"
    assert shells["beam"][:, 0].max() > 67.0 and np.ptp(shells["beam"][:, 1]) < 4.0, "the beam runs off its aim"
    from score.stages.place_build import scene_package
    bodies = {body["name"]: body for body in scene_package.hazes_of(stage, "yard")}
    assert (bodies["mist"]["shape"], bodies["puff"]["shape"], bodies["shaft_0"]["shape"]) == ("box", "ellipsoid", "cone")
    beam = bodies["shaft_0"]
    assert np.allclose(beam["apex"], [60.0, 5.0, 60.0], atol=1e-3) and np.allclose(beam["axis"], [1.0, 0.0, 0.0], atol=1e-4)         and abs(beam["length"] - 8.0) < 1e-3 and abs(beam["radius"] - 8.0 * np.tan(np.radians(10.0))) < 1e-2, beam
    hazed = [prim for prim in Usd.PrimRange(stage.GetPrimAtPath("/yard/Haze/mist")) if prim.HasAttribute("score:from")]
    assert hazed and all(prim.GetAttribute("score:from").Get().endswith(place_build.HAZE_ALGORITHM) for prim in hazed) \
        and any(prim.IsA(UsdShade.Material) for prim in hazed), [str(prim.GetPath()) for prim in hazed]
    effect = stage.GetPrimAtPath("/yard/Effects/rain")
    from score.stages.place_build import scene_package
    packaged = scene_package.rains_of(stage, "yard")
    assert [(rain["name"], rain["low"][0], rain["low"][2], rain["high"][0], rain["high"][1] - rain["low"][1], rain["high"][2],
             rain["density"], rain["fall"]) for rain in packaged] == [("rain", 60.0, 60.0, 64.0, 3.0, 64.0, 2.0, rainfall.FALL)], packaged
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
    decoded = folder / "made/cup/cup-decoded.glb"  # the take's decoded mesh as make keeps one (#209)
    decoded.parent.mkdir(parents=True)
    decoded.write_bytes(tmp_glb(out.parent))
    look = folder / "made/cup/finish/look/look.json"  # the finish route's look job, as finished/route.py keeps it (#213)
    look.parent.mkdir(parents=True)
    for name in ("mask-0.png", "mask-1.png", "decal.png"):
        Image.new("L", (4, 4), len(name)).save(look.parent / name)
    look.write_text(json.dumps({"glb": str(decoded), "masks": [
        {"slot": "white", "mask": str(look.parent / "mask-0.png"), "spec": {"recipe": "paint"}},
        {"slot": "green", "mask": str(look.parent / "mask-1.png"),
         "spec": {"recipe": "paint", "decals": [{"image": str(look.parent / "decal.png")}]}}]}))
    finish_digest = hashlib.sha256(look.read_bytes())
    for name in (decoded, look.parent / "mask-0.png", look.parent / "mask-1.png", look.parent / "decal.png"):
        finish_digest.update(name.read_bytes())
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
    # a film package's caps (#221): a map the game holds at 32 kept whole, on maps up to the film's largest, and the
    # game's caps back after
    scene_package.FILM_CAPS, film_caps = {"held_texels": 64, "largest": 128}, scene_package.FILM_CAPS
    map_bytes = io.BytesIO()
    Image.new("RGB", (64, 64)).save(map_bytes, format="PNG")
    with scene_package.capped(True) as caps:
        film_held = Image.open(io.BytesIO(scene_package.taken_down(map_bytes.getvalue())[0])).size, scene_package.LARGEST
    game_held = Image.open(io.BytesIO(scene_package.taken_down(map_bytes.getvalue())[0])).size, scene_package.LARGEST
    scene_package.FILM_CAPS = film_caps
    assert (caps, film_held, game_held) == ({"use": "film", "held_texels": 64, "largest": 128}, ((64, 64), 128),
                                            ((32, 32), 64)), (caps, film_held, game_held)
    scene_package.DENSITY, scene_package.LARGEST, scene_package.HELD_TEXELS = 512, 4096, 2048
    # a character at a time: the leader written before the crowd's first person is made, so no two are held at once
    assert events.index(("written", "leader")) < next(at for at, (what, path) in enumerate(events)
                                                      if what == "made" and "crowd" in path), events
    assert (out / scene_package.BAKE / "kept.done").is_file() and not (out / "old.json").exists()
    scene = json.loads((out / "scene.json").read_text())
    assert scene["textures"] == {"use": "game", "held_texels": 32, "largest": 64}, scene["textures"]
    copies = {copy["name"]: copy for copy in scene["instances"]}
    # the re-finished take's maps alone shaded by its own occlusion and the seams of its decoded mesh (#209)
    cup_file = scene["objects"][copies["cup"]["object"]]["file"]
    shades = {job["gltf"]: job["shade"] for job in asked if job.get("shade")}
    assert (set(shades), all(bool(job.get("shade")) for job in asked if job["gltf"] == cup_file),
            shades[cup_file]["decoded"], shades[cup_file]["decoded_sha256"]) == (
        {cup_file}, True, str(decoded.resolve()), hashlib.sha256(decoded.read_bytes()).hexdigest()), shades
    # its maps bake its finish route's masks and decals, keyed by every file of them, the copy unstretched (#213)
    assert shades[cup_file]["finish"] == {"look": str(look.resolve()), "sha256": finish_digest.hexdigest(),
                                          "stretch": None}, shades[cup_file]
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
    assert scene["objects"]["cabinet"]["library"] == "model/cabinet@1", scene["objects"]["cabinet"]  # #143
    assert np.allclose(crate["surface/boards@1"]["pbrMetallicRoughness"]["baseColorFactor"], (1, 0, 0, 1))
    assert crate["surface/boards@1"]["doubleSided"] is True  # an opaque look drawn from both sides, as Cycles draws it
    assert np.allclose(crate["surface/steel@1 top"]["pbrMetallicRoughness"]["baseColorFactor"], (0.3, 0.3, 0.4, 1))
    sand_look = dune_looks["surface/sand@1"]["pbrMetallicRoughness"]
    assert np.allclose(sand_look["baseColorFactor"], (1.0, 0.2158605, 0.0, 1.0)) and "baseColorTexture" in sand_look
    assert np.allclose(np.array(dune_uv["max"]) - dune_uv["min"], 2.0 / 0.5)  # the 2 m box over a 0.5 m tile
    assert copies["big"]["collider"] == {"shape": "convex hull", "dynamic": True, "mass_kg": 100.0}
    assert copies["wall"]["collider"] == {"shape": "mesh", "dynamic": False} and copies["crate"]["collider"] is None
    assert [(lamp["name"], lamp["kind"]) for lamp in scene["lamps"]] == [("bulb", "point"), ("flood", "spot"),
                                                                         ("sun", "sun"), ("moon", "sun")]
    flood = scene["lamps"][1]  # a floodlight: shines from its spot toward its aim, its cone and soft edge kept
    assert np.allclose(flood["shines"], np.array([0, -8.0, 6.0]) / 10.0, atol=1e-4) and flood["cone"] == 20.0
    assert flood["softness"] == place_build.SPOT_SOFTNESS and "shines" not in scene["lamps"][0]
    bulb = scene["lamps"][0]
    assert np.isclose(bulb["strength"], bulb["intensity"] * np.pi) and bulb["watts"] == bulb["strength"]
    assert np.isclose(scene["lamps"][3]["strength"], scene["lamps"][3]["intensity"] * 4.0)  # the render's sun units
    assert {"walker", "sky", "crew"} <= {item["name"] for item in scene["left_out"]}
    assert [rain["name"] for rain in scene["environment"]["rain"]] == ["rain"], "the rain falls in the game, not left out"
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
    scene_package.HELD_TEXELS = package.HELD_TEXELS = 32  # the game's side under the sand's 62: held taken down
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
        [f"{name}.glb" for name, piece in scene["pieces"].items() if "made" in piece] + ["pictures"])
    mesh = (out / "meshes/box_piece.glb").read_bytes()
    mesh_document = json.loads(mesh[20:20 + int.from_bytes(mesh[12:16], "little")])
    assert scene["pieces"]["box_piece"] == {"library": "kit/box_piece@1", "digest": "d-kit/box_piece@1",
                                            "parts": ["geo", "rim", "top"], "size": [1.0, 2.0, 0.5], "triangles": 14,
                                            "mesh": "meshes/box_piece.glb", "sha256": hashlib.sha256(mesh).hexdigest()}
    assert sorted(item["name"] for item in mesh_document["meshes"]) == ["geo", "rim", "top"]  # a USD-only kit piece
    assert scene["pieces"]["cabinet"]["gltf"] == "cabinet.glb"  # the glTF its laid cabinet.usdc was converted from
    assert scene["pieces"]["cup"]["mesh"] == "meshes/cup.glb" and "gltf" not in scene["pieces"]["cup"]  # re-finished
    assert pieces.engine_source(["cup.glb", "cup-final.glb"], "cup-final.usdc", ["part_0"]) == {"gltf": "cup-final.glb"}
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
    assert scene["pictures"]["unread"] == [] and scene["pictures"]["held"] == {"surface/sand@1/colour.jpg": {
        "file": scene["pictures"]["held"]["surface/sand@1/colour.jpg"]["file"], "size": [32, 32], "from": [62, 62]}}
    held_sand = out / scene["pictures"]["held"]["surface/sand@1/colour.jpg"]["file"]
    assert Image.open(held_sand).size == (32, 32) and held_sand.parent == out / "made/pictures"
    written = io.BytesIO()
    Image.new("RGB", (64, 8), (200, 0, 0)).save(written, format="PNG")
    picture, keys = written.getvalue(), np.arange(6, dtype=np.float32).tobytes()
    after = len(picture) + -len(picture) % 4  # the keys' view, after the picture's
    embedded = scene_package.packed({"images": [{"bufferView": 0, "mimeType": "image/png"}], "bufferViews": [
        {"buffer": 0, "byteLength": len(picture)}, {"buffer": 0, "byteOffset": after, "byteLength": len(keys)}],
        "accessors": [{"bufferView": 1, "componentType": 5126, "count": 2, "type": "VEC3"}],
        "buffers": [{"byteLength": after + len(keys)}]}, picture + b"\0" * (after - len(picture)) + keys)
    apart, held = pieces.pictures_apart(embedded)
    scene_package.HELD_TEXELS = package.HELD_TEXELS = 2048
    apart_document, apart_binary = scene_package.unpacked(apart, None)
    [(name, data)] = held.items()
    assert name == f"pictures/{hashlib.sha256(data).hexdigest()}.png" and apart_document["images"] == [{"uri": name}]
    assert Image.open(io.BytesIO(data)).size == (32, 4)  # the picture once, apart, at the game's side
    view = apart_document["bufferViews"][apart_document["accessors"][0]["bufferView"]]
    assert apart_binary[view["byteOffset"]:view["byteOffset"] + view["byteLength"]] == keys  # the keys still read
    assert copies["leader"]["looks"] == {"*": "own-leader"} and scene["pieces"]["leader"]["skinned"] is True
    assert copies["leader"]["plays"] and copies["big"]["collider"]["mass_kg"] == 100.0
    assert scene["environment"]["grade"] is None and scene["lamps"][0]["name"] == "bulb"
    index = json.loads((root / "index/kit.json").read_text())
    index["entries"][0]["digest"] = "changed"
    (root / "index/kit.json").write_text(json.dumps(index))
    (out / "made/kerb.glb").write_bytes(glb + b"    ")
    del copies["crate"]["looks"]["top"]
    scene["environment"]["exposure"] = 0
    held_sand.write_bytes(held_sand.read_bytes() + b"    ")
    (out / "scene.json").write_text(json.dumps(scene))
    found = package.problems(out)
    assert any("its exposure 0 is no positive number" in line for line in found) and any(
        "picture surface/sand@1/colour.jpg" in line and "does not hash" in line for line in found), found
    withdrawn = package.problems(out, held={"kit/box_piece@1": {"digest": "d-kit/box_piece@1", "state": "withdrawn"}})
    assert any("piece box_piece: its digest" in line for line in found), found
    assert any("kerb.glb does not hash" in line for line in found) and any(
        "(crate): its part top has no look" in line for line in found), found
    assert any("kit/box_piece@1 is withdrawn" in line for line in withdrawn), withdrawn
    copied = Usd.Stage.CreateInMemory()  # a SimReady model: each mesh its own copy of one material of one name
    for mesh_name, grey in (("door_a", 0.5), ("door_b", 0.5)):
        mesh = UsdGeom.Mesh.Define(copied, f"/kit/{mesh_name}")
        mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
        mesh.CreateFaceVertexCountsAttr([3])
        mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
        look = UsdShade.Material.Define(copied, f"/kit/{mesh_name}/looks/metal")
        shader = UsdShade.Shader.Define(copied, f"/kit/{mesh_name}/looks/metal/shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(grey, grey, grey))
        look.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        subset = UsdShade.MaterialBindingAPI(mesh).CreateMaterialBindSubset("metal", Vt.IntArray([0]))
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(look)
    assert sorted(pieces.part_corners(copied.GetPrimAtPath("/kit"))[1]) == ["metal"]  # one part, its one look
    UsdShade.Shader.Get(copied, "/kit/door_b/looks/metal/shader").GetInput("diffuseColor").Set(Gf.Vec3f(0.9, 0, 0))
    with pytest.raises(place_build.Refused, match="its part metal wears two looks"):
        pieces.part_corners(copied.GetPrimAtPath("/kit"))  # a copy that tells another look is two looks
    door_a = UsdShade.Material.Get(copied, "/kit/door_a/looks/metal")
    assert pieces.own_look(copied.GetPrimAtPath("/kit"), door_a)  # its own bake, no library surface named
    door_a.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set("surface/wood@1")
    assert not pieces.own_look(copied.GetPrimAtPath("/kit"), door_a)  # a library surface bound inside the model
    card = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 2], [0, 1, 0], [0, 1, 2], [0, 0, 2]], dtype=float)  # a +x face
    swatch = {"face": (card, np.tile([1.0, 0, 0], (6, 1)), np.full((6, 2), 0.3))}  # a palette swatch: one point
    page = pieces.paged(swatch)["face"][2]
    assert np.allclose(page[[0, 1, 2, 4]], [[1, 0], [1, 1], [0, 0], [0, 1]]), page  # boxed: the face spans the page,
    # read as one looking at it (+z to the left), up the piece
    own = {"face": (card, np.tile([1.0, 0, 0], (6, 1)), np.array([[0, 0], [1, 0], [0, 1], [0, 1], [1, 0], [1, 1.0]]))}
    assert pieces.paged(own)["face"][2] is own["face"][2]  # its own coordinates kept where they lay a page
    glb = pieces.made_glb(own, pages=True)
    assert b"TEXCOORD_0" in glb and b"TEXCOORD_0" not in pieces.made_glb(own)  # a made piece carries none


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
    held_lives(folder)


def held_lives(folder):
    """A character `put` holds still plays, in a game, the clip its pose was taken from, round from that second: by
    the clip the pose names, or (a scene laid before it named one) the clip time the pose equals, on a key or between
    two; one held mid-stride (a walking clip, no route) stands in `standing`; its check still skins the still pose;
    one posed from a library pose (`score:pose`) stays still."""
    from score.stages import place_build
    from score.stages.place_build import skinned
    stage = Usd.Stage.CreateInMemory()
    stage.SetTimeCodesPerSecond(30)
    asset = folder / "assets/characters/skinny.usda"
    rows = (("named", 1.0, False, False, False), ("unnamed", 1.0, True, False, False),
            ("between", 0.5, True, False, False), ("stride", 1.0, False, False, True), ("posed", 1.0, False, True, False))
    for name, frame, unnamed, posed, stride in rows:
        root = stage.DefinePrim(f"/held/{name}", "SkelRoot")
        root.GetReferences().AddReference(str(asset))
        place_build.dressed(stage, str(root.GetPath()), asset, clip="standing", second=frame / 30.0)
        held = stage.GetPrimAtPath(f"{root.GetPath()}/Held")
        if unnamed:
            held.RemoveProperty(place_build.HELD_CLIP)
            held.RemoveProperty(place_build.HELD_SECONDS)
        if posed:
            held.CreateAttribute("score:pose", Sdf.ValueTypeNames.String).Set("character/hold")
        if stride:  # the pose names a walking clip the body has: it walks no route, so it stands
            walking = UsdSkel.Animation.Define(stage, f"{root.GetPath()}/Animations/walking")
            walking.CreateJointsAttr(["hips", "hips/chest"])
            walking.CreateTranslationsAttr().Set(Vt.Vec3fArray([(0, 1, 0), (0, 0.5, 0)]), 0)
            walking.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1), Gf.Quatf(1)]), 0)
            walking.CreateScalesAttr().Set(Vt.Vec3hArray([Gf.Vec3h(1), Gf.Vec3h(1)]), 0)
            held.GetAttribute(place_build.HELD_CLIP).Set("walking")
        glb, facts = skinned.character_glb(root)
        assert facts["plays"]["animation"] == ("Held" if posed else "standing"), (name, facts["plays"])
        if not posed:
            assert facts["plays"]["loops"] and abs(facts["plays"]["starts"] + frame / 30.0) < 1e-6, (name, facts["plays"])
        assert facts["checked"] == "Held" and skinned.check_of(root, glb, facts)["pass"], (name, facts)


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
    larger = render.queued("job", "script.py", [], memory_gb=12)
    needs = [scene_package.run_needs(sized) for sized in ([{"size": [4096, 4096]}], [{"size": [8192, 8192]}] * 6)]
    assert needs == [(6, 1800, 4), (21, 6040, 11)], needs
    assert "MemoryMax=8G" in command and "MemoryMax=12G" in larger and "OOMPolicy=continue" in command, larger


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
    left kept, and its wall still wearing the look laid on it."""
    place_build.blocks(folder, "block", [[0, 0, 0, 4, 3, 6, "wall"], [-0.3, 0, 0, 0, 3, 6, "base"]], at=(40, 0, 0),
                       turn=(0, -90, 0))
    place_build.surface(folder, "block", "surface/steel", part="wall")
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
    walls = place_build.parts_of(prim)["wall"]
    assert all(UsdShade.MaterialBindingAPI(wall).GetDirectBinding().GetMaterialPath() == f"/{place}/Looks/block__wall"
               for wall in walls), walls  # its parts' looks kept through the re-lay
    assert all(stage.GetPrimAtPath(f"/{place}/Objects/{name}") for name in ("sign", "gate", "next_block")), made
