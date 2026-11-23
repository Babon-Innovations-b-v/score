# score/stages/place_build/plan_fit/

A laid place against its plan (the 2099 judge, 2026-11-23: all 20 places 3 to 6 of 10, the causes a room laid far
bigger than its plan, blocks standing where the plan names a library thing, parts at the wrong scale, bare walls,
one small camera). `__init__.py`'s docstring has the faults and their measures; ready/ writes them in ready.json's
`plan`, and the place is ready only with none.

- **The plan is scene_record/plan.py's place-plan**, in the place's frame (x, z boxes on its floor); `plan` takes it
  in as <folder>/plan.json, refused when its own contract faults it. No plan taken in: `plan` is null, nothing judged.
- **Judged from the laid scene**: each object's world box, its `score:library` address (a model, kit or take is a
  library thing; no address or an algorithm's is a made block), its role (ready.role_of) and its `score:dress` mark.
  A structure many times an item's size (a roof, a wall) is the building, never a stand-in. People stand for an
  item only as a crowd (CROWD or more in its box, their union measured): a lone person stands in for nothing.
- **A plan's views are named views** (`plan-stand-<k>`, `plan-<doorway>`), written at `plan`; `render` with no
  `--views` draws them beside the concept's, at render.WIDTH (1920).
- **Dressing comes from the library** (`dress`): copies of one entry `put` edge to edge (their seams the panel seams)
  along a plan wall, backs on the laid wall's inner face and mounted on it, a doorway of the plan kept clear, or tiled
  over the floor; the agent picks the entry the concept's walls show and its `--front`.
- Test: `test_a_place_is_told_where_it_strays_from_its_plan.py` (an in-memory scene of boxes, no library fetch).
