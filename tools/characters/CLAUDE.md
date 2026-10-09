# tools/characters/

The characters stage: the people (and, next, the animals) a place holds, made from the place's data and put into its
OpenUSD stage as skinned characters (UsdSkel) playing their clips. Bible chapter: `architecture/components`.

- `people/` makes the bodies: one skinned, animated glTF per person (27 joints, the clips Kimodo wrote from
  sentences, a 1,220-triangle distant body and the dressed ones), from each look kept outside the repo. It moved here
  from the game 2099's `tools/crew` with its history; its own overlay has its rules. Its model steps (Kimodo, SAM 3D
  Body, GarmentCode) ran on the owner's PC before 2026-10-03 and have no cloud runner yet: the built bodies in
  `~/.farm-factory-motion/work/bodies` are what the stage reads.
- `skel_usd.py` turns a built body into a UsdSkel asset; `cast.py` writes a place's characters layer from its cast
  (`data/characters/<place>.json`). Their docstrings have the layout of each.
- **The cast is the record.** Nobody is placed who is not an entry of the place's cast, and every entry says `why`
  it is there (2099's rule, its ADR-0007: a body needs a reason to be in a place). A place where nobody is has a cast
  with no entries and a `note` saying so, so its review page says "nobody" rather than "not recorded".
- **Numbers from the source, never typed again.** A cast copies the game's or the creator's numbers with a `from`
  naming where they were read; the rules that spread a group or a crowd (`cast.py`) repeat the game's, with this
  module's own seeded generator, so the same cast is always the same people in the same spots.
- **Nobody twice, walks clear.** `cast_check.py` refuses a cast (cast.py runs it before writing) that shows the same
  person twice in a place (a named body, or a kit mix's build, face and hair: `cast.look_of`; groups are dealt a new
  look for each member) or walks somebody through a person or a thing on the stage, with a margin (owner,
  2026-10-09). The far crowd's copies are not checked: it is a crowd, not people one tells apart.
- **The characters layer is its own.** `<stage>/layers/characters.usda` sits between the creator's edit layer and
  the framework's base (`../usd/export.py` keeps it in the root); it is rewritten whole on every run, the edit layer
  never. Characters keep their names (`<entry>` or `<group>_<n>`), so an edit to one survives.
- **A crowd is one PointInstancer.** Thousands of copies of the distant body, a prototype per clip, phase and palette;
  never thousands of skinned prims. Blender 5.0.1 imports it with every prototype animated (checked 2026-10-08).
- **Check skinning against the file.** `characters_test.py` skins a body made in the test both ways (UsdSkel and the
  glTF's own joints) and compares; the real bodies agreed to about a micrometre (the leader's walk, 2026-10-08). A
  converter change that passes the numbers still needs a picture: render it (`../review/page.py`, the characters
  section) and look.
- Generated assets and layers live in the stage folder outside the repo; nothing generated is committed.
