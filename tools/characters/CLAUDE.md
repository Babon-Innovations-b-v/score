# tools/characters/

The characters stage: the people (and, next, the animals) a place holds, made from the place's data and put into its
OpenUSD stage as skinned characters (UsdSkel) playing their clips. Bible chapter: `architecture/components`.

- `maker/` makes the bodies (the prop route and the people route on its built body, run by the people's body rows,
  `score/stages/people_bodies`); `animals/` makes the animals (by hand, or by the animal rows,
  `score/stages/animals`); `clips/` reads a body's motion off a video (the video clip rows, `score/stages/video_clips`);
  `people/` holds the body model's and the clips' pieces and the join measures they use. Each has its own overlay.
- `skel_usd.py` turns a built body into a UsdSkel asset; `cast.py` holds a cast's rules and the prims the cast stage's
  characters layer (`score/stages/cast/layer.py`) lays from a place's cast record (written from its design by
  `score/stages/people_rows.py`). Their docstrings have the layout of each.
- **The cast is the record.** Nobody is placed who is not an entry of the place's cast, and every entry says `why`
  it is there (2099's rule, its ADR-0007: a body needs a reason to be in a place). A place where nobody is has a cast
  with no entries and a `note` saying so, so its review page says "nobody" rather than "not recorded".
- **Numbers from the source, never typed again.** A cast copies the game's or the creator's numbers with a `from`
  naming where they were read; the rules that spread a group or a crowd (`cast.py`) repeat the game's, with this
  module's own seeded generator, so the same cast is always the same people in the same spots.
- **Nobody twice, walks clear.** `cast_check.py` refuses a cast (the cast stage runs it) that shows the same
  person twice in a place (a named body, or a kit mix's build, face and hair: `cast.look_of`; groups are dealt a new
  look for each member, a design's people of one look each their own variant of its body) or walks somebody
  through a person or a thing on the stage, with a margin (owner, 2026-10-09). The far crowd's copies are not checked: it is a crowd, not people one tells apart.
- **The characters layer is its own.** `<stage>/layers/characters.usda` sits between the creator's edit layer and
  the framework's base (`../usd/export.py` keeps it in the root); the cast stage rewrites it whole on every run, the
  edit layer never. Characters keep their names (`<entry>` or `<group>_<n>`), so an edit to one survives.
- **A crowd is one PointInstancer.** Thousands of copies of the distant body, a prototype per clip, phase and palette;
  never thousands of skinned prims. Blender 5.0.1 imports it with every prototype animated (checked 2026-10-08).
- **Check skinning against the file.** `test_characters_play_as_their_file_and_cast_say.py` skins a body made in the
  test both ways (UsdSkel and the glTF's own joints) and compares; the real bodies agreed to about a micrometre (the leader's walk, 2026-10-08). A
  converter change that passes the numbers still needs a picture: render it (`../review/page.py`, the characters
  section) and look.
- Generated assets and layers live in the stage folder outside the repo; nothing generated is committed.
