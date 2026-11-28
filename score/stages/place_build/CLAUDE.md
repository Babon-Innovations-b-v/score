# score/stages/place_build/

The placing agent's tool (#128, owner 2026-11-16): a place laid by hand from score_lib entries, step by step, until
its render reads as its locked concept (same room, layout, main objects, mood). The agent (a vision model) drives it
one command at a time and reads `compare.png` and the measures to choose the next correction; nothing here judges.

- **A place is done only through the full route** (2099 ADR-0008, owner 2026-11-26: "u fill them with quick made
  garbage and throw out the entire openusd scene, concept, the full score framework"). Before laying, read the concept
  into a full scene inventory, down to the small things. Then per row: a library entry on a strict fit, else a
  TRELLIS.2 model from its close-up (`make`); a library surface on every finish, never one flat paint. Then lay by the
  plan and run the checks. A place short of that is reported as not done, with what it lacks, and is never pinned.
  The kits below (`cockpit_kit`, `launch_kit`) are not a place's content: a row they cover is remade by the route.
  No stand-ins in a taken-in version. Where a place's people stand, face and walk is part of the scene, not the game's.
- **A concept's cut is the camera's, never the building's** (owner and the 2099 session, 2026-11-19). Every inside
  place is built closed: walls, roof, floor, and a door shut in each doorway (glass and windows in their openings).
  A concept drawn as a cut-away or section (a front wall missing, a roof lifted off) is a camera's look: build the
  wall, then list it with `cut <folder> <object>` (place.json `cut`), and the preview and the film leave it out of
  the camera's rays alone (blender_views.camera_cut; it still shades), the film's camera path passes it. The walkers,
  the physics check and every game engine (the scene package) get the building whole. The check (ready/) fails an
  inside that sees the sky or the outside through a gap no door, window or glass closes. A cut object is found at render by its prim's path (Blender 5's
  reader names a single-mesh Xform for its mesh), and `remove` drops it from the cut. An outside place is marked
  `kind <folder> outside` (place.json `kind`): the check then judges only its structures' rooms.
- **Everything laid comes from the library.** A withdrawn entry is refused (the owner retired every old model,
  kit, character and surface on 2026-10-21), and the finish check fails one already laid. A withdrawn entry that
  names its replacement (`replaced_by`, #155) is laid as the end of that chain (`resolved_address`), refused only when
  that end is withdrawn too. The replacement of a model or kit piece is laid in the old one's footprint
  (`in_footprint`): turned by quarters so its front is where the old front was (both records' `usd.front`) or its long
  side along the old one's, centred on it and on its floor, moved the least that clears every other object but the
  ground and what rested on the old one (set back on it after; a mount, `wall:<it>`, mounted again on its face at its
  height), refused naming what it would cut when no spot within a metre is clear. The old one is measured by its
  USD files alone; when they are out of reach the replacement is laid at the asked pose, its answer saying so. A model's record's `usd` root is the file laid (an adopted set's root, never a payload
  beside it), and its layers are only `<root>_<layer>` files in the root's own folder; its `usd.meters_per_unit`
  is laid as its own unit scale op (`xformOp:scale:units`, after the agent's scale), its `usd.up_axis` against the
  scene's (y) as its own turn after that (`xformOp:rotateX:upAxis`, `uprighted`: a Z-up SimReady model stands up, so
  the agent's turn, rest and support work on the upright asset), and a mass is weighed only by the agent's scale
  (`units_of`), never the unit conversion. A SimReady model's shapes and materials stand under instanceable prims:
  every read of what an object draws, wears or weighs walks with `Usd.TraverseInstanceProxies()` (a plain PrimRange
  stops at the instance), and nothing writes onto an instance proxy (its asset's own values stay). `put` lays only an entry
  with a USD file (kit pieces, models, the
  sky domes), copied whole under the place's `assets/`; `surface` binds a library surface over everything inside the
  object (a variant's own material, or a recipe in a palette colour), so a model's baked colour never shows; `light`
  lays the library's lamp. No geometry, colour or light is made here outside a library entry.
- **The scene is a plain USD** (y up, metres, `/<place>/Objects|Looks|Lights`) that tools/usd (snap.py, resting.py)
  and sim body read as they read a place: keep that layout, never a Blender file.
- **Render through the card queue only** (`render.py`: usd_views.py, Cycles review samples, a memory-capped scope,
  more than 12 GB free), from render/still.usda: the scene without its walkers' layer (render.still_stage; the films
  draw the people); a long one is started with tools/cloud/detached.py, never waited on in the foreground. The
  X/GL libraries a box's Blender lacks come from `bash tools/blender/setup.sh` (into `blender-mcp/libs`, the default;
  `SCORE_BLENDER_LIBS` overrides it), and an exit 127 names that fix.
- **`start --split` runs SAM 3 free on this PC's card** (score/review/concept_objects.py under SCORE_CLOUD=local and
  SCORE_FREE_ONLY=1, tools/cloud/backends/local.py's segment claim); never a rented card. `--nouns` names what SAM 3 is
  asked; `split <folder> --nouns` asks a laid place's concept for more, appended to objects.json (earlier numbers kept).
- **Every shown part wears a library finish** (finished/, its own overlay): `surface` is refused over the whole of a
  model whose own paint has parts, `refinish` lays it per part from the palette, `put` does so for a model in a paint
  no library surface made, and the check (`check`, ready.json's `finishes`) tells every object that does not.
- **A made shape that reads wrong is remade** (shapes/, its own overlay): a pipe whose section swells along its run
  (a sausage) or a hard made thing with too few flat faces (a lump) is told in ready.json's `shapes`, never kept.
- **Parts.** A kit piece's or model's colour regions are GeomSubsets; `surface --part` binds a surface on one, and the
  object's whole look then goes on every shape and every other part, so no baked colour shows anywhere.
- **glTF-only entries** (our picture-made models and takes) are converted once at `put` (gltf.py): a part a material,
  each wearing its own bake and paint (base colour, metal-roughness and normal maps), a take's `-final` model first;
  `surface` puts a library surface over a part or the whole when a bake is wrong.
- **Characters** are laid as their own SkelRoot (never an Xform over it), dressed in one body group (WORN) and held
  still in a clip with tools/characters/cast.py's own steps.
- **A held prop** (`hold`, #152): a character entry's `pose.json` (tools/props/smoke_beat/hold/) sets a laid,
  held-still character's joints and marks its Held pose `score:pose`; `--prop` lays that object at the pose's hold
  frame of the posed joint (the cigarette in the hand). An `effect` entry (the cigarette's wisp) is `put` under
  Effects, role effect, its record's `usd` root laid, never the clip it plays.
- **The dome shell** (dome_shell.py, `dome`) is code-made: its shell, ribs and deck are parts for their surfaces;
  `ground` lays the same flat disc alone as the place's ground.
  In a batch, a dome's `base` [high, wide] deepens its plinth ring, `oculus` crowns it with a ring where the meridians end, `strips`
  hangs thin lamp bands inside the glass at those heights (part `strip`, for a glowing palette variant).
- **A real ground** (relief.py, `terrain`): a terrain entry is a heightfield model read from a public-domain HiRISE
  DTM (range requests, never the whole file), its own posts near the centre and wider out to the horizon, bent with
  the planet; `terrain --pad x,z,r` levels a building's site to the laid height and eases it into the ground.
- **A tinted image surface**: `surface --colour` over an image surface multiplies its colour map (the texture's
  scale; Blender's reader brings it in as a multiply), so a scanned ground takes Mars' tint and keeps its grain; the
  preview displaces a laid ground by its surface's height map when surface.json names `displacement_metres`.
- **The sky and its sun** (`sky`): a light entry's sky dome laid as the place's own `/<place>/Environment` (the
  renderer's ambient light and exposure) and a distant sun from an elevation and heading, the dome turned (`--turn`)
  so its picture's glow stands where the sun is; never a far sphere lamp.
- **The tunnel** (`tube`): the dome shell algorithm's ribbed glass tube between two domes (parts shell, ribs, deck);
  an end wall's rim is drawn in to the tube's circle, never stepped. A tube's file is cached under the place's
  `assets/algorithm/` by its sizes: delete it there after changing dome_shell.py, or the old one is laid.
- **Standing on things**: `put --rest` lays a piece's lowest point at the given height (a floor, a table top);
  `--on-ground` reads that height over the laid ground there (a rock on a terrain's relief).
- **Doors are marked, never guessed** (`door`, #148): `--opens` the walkers open it, `--slide` it slides aside along
  its face (score:move; a sliding balcony door, a lock's plug door) instead of swinging, `--lock <chamber> --side
  inner|outer` it is a pressure door of an airlock chamber, any laid object closing the chamber's air (a blocks-built
  airlock's shell too: its walls are no dome shell, so no chamber is found without the marks). A pressure door opens
  to its high-pressure side (scene_package.locks_of: the outer one into the chamber, the inner one out of it to the
  base); ready.opening is the one answer to how a door opens, read alike by the walkers' floor, walker_route's door
  times, the film and the scene package's `door` block.
- **The plan** (plan_fit/, its own overlay; the 2099 judge, 2026-11-23): `plan` takes the place-plan in; `check`
  tells a room bigger than its plan, a plan item missing, stood in for by blocks or at the wrong scale, and a wall
  dressing the plan names left bare (ready.json `plan`); `dress` lays a library piece along a plan wall or over the
  floor as that dressing. The render previews at 1920 wide (render.WIDTH) with the plan's views when none is asked,
  and `compare` gives the concept's and the render's lightness (mean L*): a place lit far brighter than its concept
  reads its dark palette as white (engineroom@7: L* 55 against 24, its gunmetal recipes drawn exactly).
- **Named views** (`view`, `render --views a,b`): inside and low views beside the concept's, their look only. A
  named view sees the building closed; `view --cut` makes it see through place.json `cut` as the concept's does
  (render.views gives each view its own `cut`, blender_views.view_cut applies it per view).
- **Image surfaces** (`surface/ambientcg_*`, CC0 PBR sets taken in with their source in each entry's provenance and
  surface.json) tile at their own `tile_metres` in the preview, box-projected in the object's own frame
  (blender_views.py); a model's bake keeps its own texture coordinates.
- **The preview's Blender script is blender_views.py**, usd_views.py with a laid ground as the ground and see-through
  looks as thin glass, patched in there so the films' and physics' renders (which key usd_views.py) never move.
- **One palette a place** (owner, 2026-11-16: "if u take a bunch of random scans, everything will look very
  inconsistent"): `palette` takes in the place's scene surface library (its surface-library output: ProcFunc recipe
  variants in its palette tokens, the ones its props were baked from) with its wear and dirt; `surface ... palette/<v>`
  lays a variant (its recipe's score_lib entry, the spec on the look) and the preview draws it as its recipe
  (tools/props/library/recipes.py: edge wear, dirt, relief) on the mesh set upright, so shells, floors and repainted
  parts share the props' finishes. The recipes need pandas beside Blender (`$PROPS_HOME/blender-mcp/pf-site`).
- **Physics-ready structure**: `dome --opening around,radius,centre` cuts glass, ribs and plinth where a tube joins
  (a collar rib round it); `tube --cap w,h` closes its far end with a wall holding a doorway (an airlock's door sits
  in it; `--cap-door <door>` cuts that doorway to the laid door's own outline, so a round hatch gets a round one, its
  hinges and latch left on the jamb; lay the door first), `trims` end its skin on the domes' glass, and its skin is solid to WALL_HIGH over its deck (part `wall`).
- **A model's own layers** (`<file>_glow.usdc`, a monitor's screen) are laid with it as children, each a part a
  surface can take (`surface --part glow palette/screen_glow`).
- **`render --final`** renders at the films' samples at 1920x1080; the views take AgX's medium high contrast look.
- **The stair core** (stair_core.py, `stairs`, owner 2026-11-16: "real walkable stairs with landings"): a switchback
  stairwell of real size (0.167 m risers, 0.28 m treads, 1.2 m flights, a waist under each so the flight below keeps
  its head height), every piece a closed solid of real thickness, its faces turned out (the walkers' floor reads a top
  by its normal), the ground slab laid in pieces (MuJoCo let a mat fall through one face across the whole place); its
  doorways cut in its walls with a hall behind each flat's door, railings on every open edge, flats' blocks either
  side and a glazed front. Panes are one face each (a closed pane's two thin-glass skins ring with light). `--one-block` keeps only the
  flats' block the entrance opens into, so a cut-away's far wall stands free to the street and the sky beyond.
  `stairs --curtain` glazes the front as a storey-high curtain wall (only the slab edges and corner piers left), so
  the concept's cut-away look into the shaft is a look through real glass; `stairs --cut` lays the front wall as its
  own object `<name>_front` (stair_core.front_alone) and lists it in place.json `cut`: the shaft stays closed and
  the camera alone sees through its front (the section the concept draws). Every doorway is recorded in place.json
  `doorways` (`<name>_door<k>`, the scene's frame); `stairs --joined <k>` leaves out the hall stub behind storey k's
  flat door, for a place of its own joined there (the flat). `stairs --street-door` cuts a street door in the
  entrance block's facade (`<name>_street`, in place of its ground window nearest the shaft): that ground floor is
  the lobby the entrance opens off, so the stairwell meets the street (#154).
- **A neighbour's part of the concept** (`backdrop <folder> <name>`, place.json `backdrop`; 2099's prologue,
  2026-11-22: the flat carried its own square, crowd, stage and far blocks through the street's walls): an object or
  lamp of the concept's surroundings that another place of the area is (place/square). The place's own renders draw
  it; its package leaves it out once the area seats it, and the area's shells check reads it as none of the place's.
- **A block giving way** (`hollow <folder> <name> --region x0,y0,z0,x1,y1,z1`): a blocks object re-laid without what
  stands in each region (the scene's frame), its boxes read back from its laid mesh and cut, its parts, pose and role
  kept; what stands wholly in a region (a shop's tables, its lamps) and fittings left with no wall within
  FITTING_REACH go with it, a door leaf never, nor a neighbouring block reaching in (each hollowed in its turn). The street's wall_l1 round the seated stairwell and flat: the walker began inside it. A ground stays the ground (the street's kerb under the stairwell's lobby, 2099 #161: one height with the lobby's floor, the two drawn through each other).
- **Places of one area** (area/, its own overlay): `join` marks the doorway leading to a neighbour place, `area` seats
  the places at the plans' storey heights with their joined doors meeting and checks every join (seats.json).
- **A physical sky from where and when** (`sky-at`, #154; every library sky dome is withdrawn): an airless body's
  sky (the Moon's) from a kept scene's sky (`--scene`, `{home}/design/sky/<scene>.json`) or a given site and time,
  written by the light stage's own `light/sky.py write` on overhead.py's answer, never a second sky model: the risen
  lights at true direction, kelvin and lux, the Sun's disc, every other body a ball at its true size and phase, black
  behind them, the backdrops' domes as the Environment's light, the exposure a white face square to the Sun at 1;
  `--turn` turns the azimuths onto the place's frame. Each body wears its library face (`surface/<body>_face`'s
  face.json, as its body-face row made it); one the library lacks or withdrew is laid named missing. A body with
  dusty air (data/physics/dust.json: Mars) gets the light layer's own day sky (#156, camp's black dome): each beam
  through its dust (`sky.through_dust`), the day dome `scene.write_sky_dome` draws for the light layer at
  `/<place>/Sky/Dome` (its picture in the folder's `assets/textures`, built by `(mars_sky.write)`), the dome's
  light on the ground (mars_sky's radiance without its gain, summed over the sky) as the Environment's, the
  exposure a white face square to the Sun at 1 under the beam and that light. A body with air the table lacks is
  refused. The light stage's gate (`sky.faults`) holds it in the test.
- **`sky --background`** sets the sky the camera sees (a palette token's night blue where the entry's is black).
- **Blocks** (`blocks`, batch only; the street, owner 2026-11-16: "no paper-thin walls, bevels on edges"): a
  straight-sided structure is solid chamfered boxes from the shell algorithm (dome_shell.blocks_file), one object of
  parts: a road and kerbed pavements of slabs laid as ground, a building's walls with its window openings, reveals and
  a shop's room as a structure (`score:role`). A window, sign or air conditioner flush on a wall is `put` with
  `role` "mount" and `support` "wall:<building>", so the check (ready/) judges it against that wall.
- **The cockpit kit** (`kit`, batch only; cockpit_kit.py, the capsule lock, owner 2026-11-23: "messy meshes, no
  panels, ugly walls, way to big for the cockpit"): a small craft built in code at real size, laid as
  `algorithm/place_build`. The capsule's body follows one cone (Cone: the hull's inner face 1.4 m from the axis at the
  floor, drawn in 0.22 m a metre up, carried on over the ceiling by the `nose` to a narrow rimmed top; every face of
  hull and lining a cone offset along its normal): the smooth hull and the quilted lining (big stuffed pillows in
  courses, each course's cushions of their own widths (CUSHION_WIDE, WIDE_SPREAD, drawn from CUSHION_SEED) and its
  seams set off from the next's at random, each a superellipse dome swelling steeply from its edge, so two pillows
  meet in a deep crease and their corners pinch in; owner 2026-11-24: "uggly creme bricks", never a flat grid of
  equal tiles with drawn lines: the crease is dark by its depth and a seam a shade under the vinyl (part seam, the
  one row of cells along each crease; round 4 the concept's caramel-brown vinyl, never creme), drawn nowhere the
  quilting is eased, a plate's roll included, and the face is shaded by the whole grid's own normals, so no
  part's or wall's edge breaks it, and a vinyl look wears no edge (a worn edge drew a bright line along every join
  of two walls); the padding curves over at the top into the ceiling (`shoulder`, `inset`), its own walls
  (`rise`) so no wall's middle stands out in the room; no seam where the quilting is eased; two fades meeting ease
  the padding between them flat together, each fade measured on the skin's face across its hole's axis as the
  hole's flange is laid (a straight line from its middle ran short at a hatch's sides, and a cushion swelled
  through the flange there); a bolster along the floor, eased flat round each hole and
  along the cut-away's outline (its section a clean band of the padding); a `mount` plate set into the padding where
  a panel or screen hangs on the wall, the lining's skin on its plane under it and a MOUNT_BORDER band round it and the
  cushions it cuts swelling from a crease beyond that, never puckered or ragged round it (`flats`, flat_spot) each in walls of their own
  (`sector`, 30 degrees; a lining's wall ends along the seams round its cushions, never across one, so two walls meet
  in a seam with no line; a wall's middle then lies by it, so the check's rays from it never cross the room's
  furniture: lay the walls so no middle falls inside a panel, the capsule's from 15 degrees), the cut-away's `plug` its own
  object for place.json `cut` and a narrow rolled `lip` round it (part lip; through the wall's thickness from outside
  the hull to the lining's back, never into the room, so a view that does not cut sees no band across the padding;
  never a frame round the room: the judge's "TV screen"); ceiling, floor (a solid disc on the service module, two rings of
  deck plates), skirt (an open service bay of struts and pipes), nose, porthole and hatch sleeves (`through_wall`, flanges hugging the cone, the porthole's pane out past the
  hull; a hatch's outer flange bolted when 2 cm thick or more), the hatch's `tread` (ground) and leaf (a hinge arm
  across its outside; laid shut, the walkers swing it), the `gantry`
  (one railing run along one edge and round its end); instrument panels (plate and bezel one body, label strip in
  modelled letters, "A|B" two sections parted at `split` by a raised divider, each with its own strip, a "/" stacking
  a name's words), each switch, lamp, gauge, screen, seat (a padded bucket seat, `scale`) and console its own
  piece. A cabin laid for play (owner 2026-11-24: "chair in middle, joystick with trottle in front"): the seat in the
  middle, the console before it (stick under the right hand, throttle under the left), the screens on mounting plates
  straight ahead at seated eye height, and the labelled panels on `console` pods in an arc round the seat, each
  pod's sloping top square to it and within seated reach, one panel a pod, none over another; nothing he needs
  behind him (the capsule's: the pilot faces 52 degrees, the hatch behind his right shoulder with its way clear, the
  second seat behind his left; two wings front-left and front-right, and at each hand a low desk with a steeper riser
  behind it, its panel above the desk's). A console's deck and lip sink a little into its top, sharing no face with it. Every part takes its look from `looks`; a part with none is refused. Every piece is closed, nothing in it
  shares a face with another and no face is collapsed (a reader drops it and every part's face numbers after it
  slip: the floor drew black); a hole is cut only within THROUGH of its wall (its axis runs on to the far wall). A
  piece's file is cached by its sizes under `assets/algorithm/place_build/`: delete it there after changing
  cockpit_kit.py. `kit --ground` lays a piece as the walked ground. A real cabin's look (owner 2026-11-24: "look up
  a real cockpit of a rocket ... that light padding just ugly"): the lining's `panels` (CONE) lays it as a real
  cabin's wall, that many padded panels round, their joints lined up from `panel_from` so one panel is one wall of the
  lining, the joints running on to the fitting they meet, the kick pad along the floor still quilted; panels are
  screwed down round their bezels; a toggle's `guard` is its wickets (the Apollo command module's), "cover" the red
  flip cover of a critical switch; the hardware takes a valve handwheel, a guarded push button, push-pull circuit
  breakers, an attitude ball, and a wall's grab `handrail` and clamped `cables` run. Round 2 (the judge: "still
  quilted padding ... no painted-metal wall panels, no bolted structure"): the cone's `panel_puff` a few millimetres
  and `quilted` empty make the lining charcoal painted metal panels, its walls' `screws` (wall_screws, in the wall's
  own piece: a curved row of screws of its own had its middle behind the face) screwed along every joint clear of
  holes, plates and the cut; lamps sit in a black bezel with a low lens, an `annunciator` lays them in a grid (unlit
  ones "off", dark glass), the ball carries its pitch lines and roll scale, `talk_key` is the radio's rubber
  push-to-talk key, and a toggle's plate is dark (a bright plate read as a toy block). Round 3 (the judge: "bare bat
  switches", "a plain light-tan disc" for the hatch): a toggle's wickets are stout bails on feet standing over the bat
  (a thin wire beside it read as no guard), the hatch leaf's inside carries eight ribs from its wheel's hub and a lit
  ring inside its rim (part lamp_white), and a panel's label is 14 mm by default (20 mm read as game lettering). Round 4
  (the judge: "a toy or a pool float" handwheel, "a glowing outline" round "a flat dark disc", guards blurring "into
  blobs", breakers "tiny dots"): a `wheel` is machined, one true round rim, three round spokes and a chamfered hub (its
  `part` "metal" on the hatch); the hatch leaf's lit ring is gone and it carries its locking gear, a gearbox drum
  under the wheel and eight latch dogs at its rim on link rods; a toggle's wickets are 5.6 mm bars a third taller
  than the bat; `breakers` takes a `size` (the wall rows at 1.3, an index tick under each); `talk_key` takes a
  `guard`, a bar each side arching over it. Night wave 2 (the judge: "blank placeholder boxes"): a closed panel's
  `cover` is a real bay cover (a pressed bead, a knuckled piano hinge, two quarter-turn fasteners, a riveted data plate
  of engraved lines, no word), and the lining's joints are left to the panels' own roll (a `seam` look darker than the
  wall drew them as broken floating bars on the lining's cells).
- **The cabin shell** (`kit`, batch only; cabin_shell.py, laid as `algorithm/cabin_shell`; 2099 #246, the owner: a
  real Apollo/Soyuz-like cabin, flat Beta-cloth panels, no quilted padding; ADR-0008: a structure row laid by its
  inventory row, never a kit stand-in): the cabin's structure inside the capsule's cone (cockpit_kit.Cone).
  `cabin_wall` (rows wall lining panels, lining panel frames, wall ribs): a flat panel between each two `joints` (from
  4 degrees, 24 apart: the capsule lining's own, its walls' mounts laid by them; a porthole on a joint cuts both
  panels, the joint's frame and rib stopping at its flange) and each two course lines (COURSES, then the
  shoulder's straight chamfer in INSET to the ceiling ring), each a flat slab inscribed in the cone (on a cone its four
  corners lie in one plane) SEAM short of its joints, a recessed frame channel under every joint, a riveted T-section
  rib over each upright joint of the wall courses, round-headed fasteners along every panel edge; holes, `fades`, the
  cut-away's `plug`, `sector` and `rise` as the cockpit lining's. `cabin_floor` (rows floor, floor plate seams): a
  deck of removable walkway plates (four in the middle disc, `plates` round it) whose open seams show the joists under
  them, countersunk fasteners at their corners, and the bay's bulkhead at the hull's foot, the bay between clear for
  the underfloor rows. `cabin_ceiling` (row ceiling lining): a flat middle panel and a ring of flat panels over a
  backing plate. Parts panel, back, frame, rib, fastener; deck, joist, fastener, bay; each takes its library surface
  per part. Nothing in it shares a face with another part (a fastener's foot sinks SEAT into its seat).
  The instrument side (2099 #246, 2026-11-28: the panels from one picture failed twice from TRELLIS.2): each panel is
  a code plate the library hardware sits on, built in a made model's frame (origin at its foot's middle, y up, front
  +z, depth centred), so the inventory's spots hold: `instrument_panel` (housing, face plate, a bezel of four convex
  bars: a ring's middle lies in its hole, where the check read the panel inside the gauge standing there; fasteners),
  `display` (a screen's dark glass part `glass`, `header` bezel over it for its lit label), `attitude_ball` (part
  `ball_sky` over `ball_ground`, the front half of a ball standing on its plate, which the game turns round its
  middle), `gauge` (part `dial`), `console_desk` (cockpit_kit.console's box), `porthole` (sleeve, flanges, bolts and
  pane through the cabin wall, in the capsule's frame). The game's faces (GAME_FACES) are written turned half round
  y, front -z as the game's cockpit reads a display, and laid turned back. No body of a piece overlaps another (LIFT).
- **The launch kit** (`kit`, batch only; launch_kit.py, the pad, the 2099 judge 2026-11-23: "the wrong ship and looks
  messy", "a plain grey rectangular slab box", "stair-stepped block zigzags"): a launch site's big pieces in code at
  real size, laid like the cockpit kit's (same `kit` step, looks, cache): the steel ship of welded rings with its
  black-tiled nose, flaps and engine bells inside the aft skirt it stands on; the round launch ring on legs with
  clamps, hoses and orange-lit boxes; a tower's straight X-bracing (a `blocks` tower keeps its posts, cabin and roof,
  its stepped boxes dropped) on flat-topped girders a lamp stands on; a platform railing; a floodlight's 3 x 3 head;
  a far city's glass towers, its big wheel and smooth hills (marked `fixed`: far scenery, never in the walkers' grid);
  a harbour ferry with its lit window bands and its wake on the water; a harbour's `water`, one closed flat-shaded
  slab whose top grid is finer near the place (blocks draw smooth: a 12 km strip leant its top from its chamfers and
  the near water mirrored the city in a patch with a ruler-straight edge; the check keeps a ground's faces by their
  corners near the place, so one huge face would be dropped); a `coast` under that water (2099 #161, the owner: "zero
  terrain", the pad on a flat plane with no land, shore or sea round it): one closed heightfield solid, its seeded
  shoreline at the waterline, land rolling up inland in hills (part land: a grass, soil or rock look), a shore band
  rising to its berm and the sea bed sinking under the water (part shore: the library's sand or rock), each `sites`
  [x, z, radius, height] levelled (the launch deck, the square's promenade) and eased into the land; laid `fixed`,
  or `kit --ground` where it is walked. The ship with `ring` 0 is one seamless steel
  barrel (the pad's judge: "evenly spaced ring bands"), its canards and aft flaps sized by `fore`, `aft`, `aft_chord`.
  The pad's join to the capsule (2099 #161, 2026-11-24: the walkway's 1.41 x 2.06 m door led into the ship's steel):
  the ship's `hatch` makes its skin a band `thick` deep from `low` to `high` round a hollow the crew capsule sits in,
  opened by `rows` (the hatch frame's outline and the capsule's bulge, seen along the arm's level way), the hull under
  it and the nose over it closed solids HATCH_GAP apart; a `door_wall` is a flat wall holding a doorway of a door's
  own outline (`rows` [up, left, right] from the doorway's middle), its doorway recorded in place.json `doorways` as
  `<name>_door` (`of` the piece), so the arm's end is cut to the capsule's round hatch and joined there with no leaf
  of its own (one leaf a join: the capsule's hatch). `remove` takes a removed object's doorways and the joins read
  from it or them out of place.json.
- **Pipe runs** (`pipe`, batch only; pipe_run.py, `algorithm/pipe_run`, 2099 ADR-0008, 2026-11-26): a place's long
  thin parts from the library, never a picture's model of a pipe: a run laid along its `spec`'s `path` (or `paths`)
  with its `profile` (round pipe, conduit, drainpipe or rail; corrugated hose; cord; bundle of cables; flat strap; box
  bar or rib; channel tray; railing of posts, rails and bars (balusters, `bar` their radius) or glass), `sag` a flexible run's catenary between its
  points (an overhead cable, a lantern string), its corners bent on a bend radius, a rigid run's elbow sleeves over
  ELBOW_TURN, collars every `joints`, caps, `wall` brackets every BRACKET_GAP (clamp, stand-off, plate), a bundle's
  ties, a strap's buckles, a bunting's `pennants` (a flag hanging at each `hang` spot); one section all along (never a sausage), every piece closed; each part (the run's own, `fitting`,
  `bracket`, `post`, `infill`, `buckle`, `pennant`) wears its look from `looks`, refused when one has none. Its answer gives the
  run's length and its `hang` spots in the scene's frame, where a string's lanterns are `put`. Cached by spec and
  code under `assets/algorithm/pipe_run/`.
- **A night** (`night`, batch only): no sky picture; the night's physics (score/stages/light/night.py worked out for
  the place: the moonlit and city-lit air, the moon) passed in as the Environment's light, background and exposure
  and a moon light; its `sky` names what of the night is drawn, each a library surface (refused for another kind or
  a withdrawn one): `stars` (surface/stars_hyg8, surface/milky_way_eso), `cover` the share under cloud as the concept
  shows it (an overcast night, cover 1, shows no stars) and `moon_face` (surface/moon_face) only where the concept shows
  the Moon, carried into the package's `night` for the game's sky to draw; `haze` a body of haze (tools/usd/scene.py's haze body) the renderer fills, a box or, with
  `shape`, an ellipsoid or a cylinder (a steam plume's puffs round, never a box's stair-stepped edges); `shaft` a
  lamp's cone of lit air (scene.py's write_shafts under Haze/<name>: a floodlight's beam, never a box of haze, whose
  straight edge cut the pad's near water off from the rest).
- **`batch`** runs many steps in one process on one open stage: a full relayout in seconds, never one call a step.
- **`review`** (review.py, review_views.py; owner 2026-11-16: "were missing a tool that allow for quick ways to review
  a scene"): a region (the scene, `--box x0,z0,x1,z1` or `--prefix`) as one contact sheet from one Blender call on the
  card at 8 samples denoised, the ground's displacement as bump (a review never ships): a plan cut 2.4 m over the floor
  with a 1 m grid and names, four corners, eye height from each door and the middle, a close-up per compartment
  (place.json `compartments`, else each dome shell structure), the concept in the corner, review.json listing the
  views; a physics check's faults (`check.json` {"faults": [{"object", "kind"}]}) boxed in red. A crowd of one entry
  (the stones) never frames the region. `viewer` writes the scene as one Draco GLB (viewer_glb.py, no card), its
  textures halved until it fits 15 MB, for the owner to orbit.
- **A square's crowd** (`crowd <folder> --toward <object>`, crowd.py; 2099 #161, owner 2026-11-26: "people walking
  through walls and the stage"): where every person of a crowd stands, faces and walks is the scene's. Its laid people
  (`--people`, `person*`) are turned to face the leader by their toes (score_lib's people face their model's -z); the
  floor round them packed (`crowd`, a PointInstancer of PROTOTYPES of them, shoulder to shoulder before the leader,
  thinning away); two walkers' lanes laid out through it (`crowd_walkers`, each walker's far end in `score:walks_to`,
  the piece list's copy `walks`). Every spot is kept only where nine rays down its body's column find the crowd's
  floor with nothing within HEADROOM over it and no solid round it (an odd count of faces over a point: inside a
  wall), and where level rays from its middle meet no solid within its body's reach (REACH, or the prototypes' posed
  skins' most) nor one object all round (inside a hollow building: the square's east tenement held 51 copies, one
  with its hands 26 cm in its facade), every lane step where its corridor does; a laid person whose column is not clear, or who stands on a lane,
  is taken out. Every laid person and copy then stands by its feet as the check reads them (`stood`, `stood_rows`:
  its lower foot on what is under it, taken out where the other would stand over STEP off), and the copies' turns are
  written in float too (`orientationsf`: a half quaternion is never unit length, so each copy read 0.05% stretched and
  the package converted all 2,038 apart, 24 GB). The check reads a crowd copy by copy under the package's names
  (`<crowd>_<n>`, ready/people.copies_posed), never its prototype at the origin. A game only draws them.
- **`make`** (maker/, its own overlay): a prop's model made with TRELLIS.2 on this PC's card from its picture (a take's
  close-up, a concept crop by its SAM 3 mask), set over the model it replaces, graded to the palette, CoACD hulls and
  mass, taken into score_lib as a draft entry that `put` lays like any made model.
- The camera `start` writes is a starting guess (`CAMERA`); the agent sets the concept's with `camera`.
- **The film** (film.py, `film`, `film-render`; owner 2026-11-16: "get me my demo"): a camera path that holds on the
  concept's view, glides down clear of everything and moves through the place's stops (named views with their aims,
  `x,z` at eye height over the floor walked by tools/usd/camera_paths.py's legs, or `x,y,z` in free air; `>x,y,z`
  aims one), against the physics check's own solids (ready.Place, its lights left out, each door as it stands for
  the walkers: one marked `score:opens` swung open). Its speed and look are eased,
  never jump; a frame carries the stage's time code, so walkers laid as time samples move with it. A glazed or closed
  place is filmed from free air outside its glass, never through a closed door.
- Test: `test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them.py` (no Blender, no library fetch;
  blender_views.py is checked by a render of the fixture scene, never in the test).
- **The scene package** (scene_package.py, `package <folder> <out>`): the laid place for a game engine (2099's Unity,
  glTFast) in tools/props/library/package.py's one format (score.scene v1, checked by its own check, never forked):
  every object converted from the laid USD with usd-core and trimesh's writer (a door a walker swings over time laid
  as it rests, with its `door` block; any other moving object left out), laid at place.json `seat` when the area
  gave one (area/), its bound looks as glTF PBR (exact
  factors, maps, an image surface box-projected over its tile, glass as transmission), an unchanged glTF model its
  entry's own glTF; colliders from ready.json's roles. A palette recipe is baked as the preview draws it (wear, dirt,
  relief; bake_looks.py, headless Blender through the card queue) at 512 texels a metre on xatlas maps, each map as
  big as its charts and at most 4096 (written at most 2048 and every side a multiple of BLOCK_TEXELS, 4, so an engine compresses it in its 4 x 4 blocks;
HELD_TEXELS: the game's PlaceTextures.MostTexels, a
  bigger picture halved as its mip is made, so the game decodes what it shows; 2099 #161) (a face wider than half a map cut first, blocks of a map's worth packed alone, a
  map under 512 refused: #146, #151; the base's hangar sat 11.5 h packing 44 big faces as one 33,000 px map), a laid
  ground's as one seamless 8 m tile, a picture-made model's parts (a take, a TRELLIS.2 model) shaded as the bench
  draws its look (shade_of, #209: its base colour darkened by the model's own ambient occlusion, every part shading
  each map, and in the seams of its decoded mesh where make kept it in made/; where `finish` ran the finish route on it in the
  place, its texel masks and decals baked from the model in place of its parts' palette variants at the place's wear,
  finish_of, #213), in Blender runs of a few maps of one object each (scene_package.BATCH; one run
  over the street's 225 maps grew past the 8 GB cap), SIDE_BY_SIDE runs at once on measured card shares (a run's
  card mostly waits on its Blender's processor work: 29% busy one run at a time, 2026-11-22), each finished map marked under <out>/bake/maps so `package`
  again resumes a stopped bake and rebakes only a changed object's maps; every step runs under its time
  (scene_package.STEP_SECONDS: an object's conversion and the scene's rest stop the process with its stack, a Blender
  run is stopped by `timeout`, its card wait not counted), each named in <out>/bake/steps.log first; a mesh with no
  normals goes smooth, as Blender imports it; scene.json's
  `environment` carries the sky picture, sun, exposure, the ground's baked albedo (an engine's bounce from below) and
  the AgX grade drawn by Blender's own OpenColorIO as a lattice picture (grade_lut.py), so the engine grades exactly.
  **`package --draft`** (2099 #161) is a preview that never ships: the same scene.json and glTF objects with no bake
  and no walkers' eyes read, each palette recipe its plain colour, metal and roughness (an image surface keeps its
  own pictures), scene.json `draft` (scene_package.DRAFT); score-lib take-in --place refuses a folder carrying it.
  **`package --pieces`** (pieces.py, 2099 #245) writes the piece list beside it, score.scene version 2 in package.py's
  format and check: no Blender and no bake, in seconds. Its `rests` is how its copies rest by the place's check
  (ready.json, pieces.RESTING: floating, no support, tilted, tips; null with no check or one older than the scene), and
  a list with any is refused (2099 #161, owner 2026-11-26: objects floating and standing at wrong angles in every place);
  2099 fetches a pinned place only with `rests` [], so run `check` after the last lay and before the package. A laid library entry (model, take, kit, effect, ground) is a
  piece by its address and its index's digest, never written; everything made for the place (an algorithm's blocks,
  stair core, dome, terrain) a made/<name>.glb of one mesh a part, positions and normals only; each copy its whole
  matrix and a look id a part (a recipe's spec word for word, a surface's factors and library maps, or `own`).
  **Characters go in it skinned** (skinned.py, 2099's prologue, 2026-11-20): every SkelRoot laid (a `put` player
  model, the cast's characters layer, a sim body's own SkelAnimation) and every crowd PointInstancer copy is a skinned
  glTF converted from the laid USD (its skeleton, shown meshes with their weights and morph targets, every clip cut to
  one round and the animation it plays, a walker's route as node 0's moves), its copy's `plays` saying from when; its
  check skins the glTF at the played animation's first, middle and last keys against UsdSkel's own skin (within
  1e-4 m) and fails the package otherwise. The people's correctives key negative weights: an engine must not clamp
  them (Blender's importer does until a key's slider_min is lowered). Prims under a SkelRoot must be typed (a Scope,
  an Xform): UsdSkel skips a skinned mesh under a typeless prim, as tools/characters/skel_usd.py's assets never have.
