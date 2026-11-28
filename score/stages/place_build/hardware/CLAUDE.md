# score/stages/place_build/hardware/

Small hardware and boxes built in code as products (2099's prologue, 2026-11-28: TRELLIS.2 from a picture kept
failing on thin parts and small hardware, its new-seed remakes failing again; the owner on the locker: "its mainly just
the lock and the holes ... make them library parts"). A wall switch, socket, door knob, lever, pull handle, picture
nail, junction box, meter box, split or window air conditioner, intercom or kerb grate is built from one vocabulary of
parts (`__init__.py`: a bevelled plate, a turned piece, a bent bar, a screw head, a cable gland, louvres, bars, a fan
guard and blades, a key), at its row's size and its approved close-up's proportions, and taken into score_lib as a
draft `model/<row>.<place>` (never `_trellis`), tagged `maker: score_hardware`.

- `python -m score.stages.place_build.hardware build <kind> <entry> --size W,D,T --out <folder> --words W
  --material <class> [--option key=json ...] [--take-in]`: the GLB `<entry>-final.glb`, CoACD hulls
  `<entry>-hulls.glb` and `<entry>.json` (the maker's record shape: `physics.mass_kg`, a real-world mass a part by
  maker/sim.py's Claude ask, EUR 0), then `score-lib take-in --save` under the maker's take-in lock.
- **Laid as a made model is**: y up, front +z, stood on y = 0, centred on x and z (fit.size_matrix's frame), so it
  lays where the row's TRELLIS.2 model lay; `grate` lies with its top up.
- **Every part is a closed solid under its own name** (a GLB material a part), so the place lays each its own library
  surface with `surface --part` (the lay plan's finishes name them); the GLB's colours are stand-in tints for a
  preview only and never a finish. Sharp edges keep their own vertices (`edged`), so the glTF reader keeps them hard.
- **Kept only when it reads as its object**: render each build beside its close-up and judge it before take-in; a
  row whose shape is not one of the kinds has no route here.
- Test: `test_a_built_product_fills_its_row_in_closed_named_parts.py` (no Blender, no library; CoACD on one row).
