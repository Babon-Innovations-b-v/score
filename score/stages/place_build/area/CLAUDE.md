# score/stages/place_build/area/

Places of one area fitted together (#150; 2026-11-20, the 2099 prologue: the walker stopped on the flat's landing and
never reached the stairwell, the flat laid at the street's level and raised by hand in the game). The CLI is
place_build's (`join`, `area`); this module seats and tells, it never moves a place's objects.

- **Where places meet is the plans'**: the outside place's kept plan `holds` the area's places, a join is a door of one
  leading to the other with a door back (scene_record/plan.py `paired`), and the storey heights are `plan.levels_of`
  (the stairwell's flat door 9 m up: the flat's floor 9 m up). Never a height typed in here or in the game. A pair
  both plans lead to each other but the holder's plan holds apart (the square held the street 45 m from the
  stairwell, 2099 #161) is still joined by its built doorways, and the plan's holds are told. The outside's own door
  to a place it holds is a join too (`with_holder`: the pad's walkway hatch into the capsule it holds at the tower's
  top, 2099 #161), the outside held at its own corner.
- **Where they meet in the built scenes is place.json `joins`** (`place_build join <folder> <doorway> <to>`): a doorway
  the stair core recorded when laid (place.json `doorways`, `<core>_door<k>`) or a door leaf of the scene (its inward
  read from the shell it is set in, else `--inward x,z`). A plan join a folder joins no doorway for is told by name.
- **Seats**: the outside is the area's frame; `--stands <place>` lays one place as laid (raised to its plan's
  storey: the flat, laid in the frame the plans name) before the rest; a place joined to a seated one is seated onto
  it (its doorway on the other's, facing it, its floor where the plans put it); when none left is joined, the lowest
  on the plans stands where the outside's plan holds it (`held_seat`, by both plans' `frame`: the street's plan names
  the half turn its built scene lies at), as laid only when the outside holds none of it, and says so. `seats.json` holds each seat (USD row-vector order, glTF's column-major)
  and its words; `--seat` also writes each into its folder's place.json `seat`, and `package` then lays the place in
  the area's frame (scene_package.seated, on the session layer: the scene file never moves), because the game lays
  an area's places where their packages put them, so no game-side offset remains.
- **The joins check**: sills within LEVEL, middles within ALIGN, facing within FACING, a leaf no wider than the
  doorway it is seated in (ready.FIT), and a walker's way WALKWAY wide from INSIDE in from one doorway to INSIDE in
  from the other over both places' objects round the join (their backdrops left out, as the game leaves them), seated, every doorway open (ready.route_on, as the walkway
  check judges a doorway a way). A failed join is fixed in the place (rebuilt) or the plan, never by a looser measure.
- **The shells check** (`shells_crossed`, 2099's prologue 2026-11-22: the walker began inside the street's block,
  the flat and stairwell seated within it): every two seated places' shell objects (SHELLS, ready.role_of; a place's
  `backdrop` left out) may stand at most CROSSED cubic metres inside each other, counted at points STEP apart inside
  both closed solids. A crossing is fixed in a place (`hollow` its block, `backdrop` its concept's stand-in), never
  by a looser CROSSED.
- **One leaf a join**: the place whose plan names the door lays its leaf; its neighbour's joined doorway stays a bare
  opening. The closed-inside check counts a look through a joined doorway as closed (ready.through_joins, #154), so
  neither place lays a second leaf to pass it.
- Test: `test_places_of_an_area_meet_at_their_doors.py` (a one-storey stair core and a room, no library fetch).
