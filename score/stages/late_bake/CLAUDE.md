# score/stages/late_bake/

A kit bake's gates (`made`, `surfaces`), read off make_kit's reports, which the ship kits' and the earth kit's rows
take. The late-bake row and its runner, which baked the camp's game kit (camp_kit.py and the old seed's made folder),
are retired (2026-10-21).

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Gates read make_kit's reports**: every planned model made, every slot a library surface (variant or printed
  picture). A part painted outside the library fails.
