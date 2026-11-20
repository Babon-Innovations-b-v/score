# score/stages/place_build/area/

Places of one area fitted together (#150; 2026-11-20, the 2099 prologue: the walker stopped on the flat's landing and
never reached the stairwell, the flat laid at the street's level and raised by hand in the game). The CLI is
place_build's (`join`, `area`); this module seats and tells, it never moves a place's objects.

- **Where places meet is the plans'**: the outside place's kept plan `holds` the area's places, a join is a door of one
  leading to the other with a door back (scene_record/plan.py `paired`), and the storey heights are `plan.levels_of`
  (the stairwell's flat door 9 m up: the flat's floor 9 m up). Never a height typed in here or in the game.
- **Where they meet in the built scenes is place.json `joins`** (`place_build join <folder> <doorway> <to>`): a doorway
  the stair core recorded when laid (place.json `doorways`, `<core>_door<k>`) or a door leaf of the scene (its inward
  read from the shell it is set in, else `--inward x,z`). A plan join a folder joins no doorway for is told by name.
- **Seats**: the outside is the area's frame; a place joined to a seated one is seated onto it (its doorway on the
  other's, facing it, its floor where the plans put it); when none left is joined, the lowest on the plans stands as
  laid and says so. `seats.json` holds each seat (USD row-vector order, glTF's column-major) and its words, for the
  game to lay each place by, so no game-side offset remains.
- **The joins check**: sills within LEVEL, middles within ALIGN, facing within FACING, a leaf no wider than the
  doorway it is seated in (ready.FIT), and a walker's way WALKWAY wide from INSIDE in from one doorway to INSIDE in
  from the other over both places' objects round the join, seated, every doorway open (ready.route_on, as the walkway
  check judges a doorway a way). A failed join is fixed in the place (rebuilt) or the plan, never by a looser measure.
- **One leaf a join**: the place whose plan names the door lays its leaf; its neighbour's joined doorway stays a bare
  opening. The closed-inside check counts a look through a joined doorway as closed (ready.through_joins, #154), so
  neither place lays a second leaf to pass it.
- Test: `test_places_of_an_area_meet_at_their_doors.py` (a one-storey stair core and a room, no library fetch).
