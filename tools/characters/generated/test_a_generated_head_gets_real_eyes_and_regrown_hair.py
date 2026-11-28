"""A generated head gets real eyes behind its lids and its painted hair regrown (#223). Each break named below turns
its row red: each painted pupil
is found on the face (eyes.pupils, a pupil missed or found on a lid or brow turns it red), the eyeball sits behind
its lid margins with its cornea behind their rim (eyes.eye_depth: a ball bulging past the lids, or one sunk far
behind them, turns it red), the painted floor inside the ball is removed and nothing outside the lid opening is
(eyes.buried), the floor beside the ball is pushed straight back and no lid point moves (eyes.pushed: a lid pushed in
or a floor left standing turns it red), the wet line lies on the lids' inner rims round both eyes (eyes.wet_strip),
both eyes gaze at one point straight ahead (eyes.made's gaze, eyes.placed: a crossed or wall-eyed pair turns it red),
the iris's colour is read off the photo's iris (eyes.photo_iris: a colour read off the eye's white or the skin round
it turns it red), a lid margin is read where the lid stands, steep or gentle, never on a bump or a curve of the
painted floor (eyes.margin_along: a margin taken on the floor lets the floor beyond it cover the iris and turns it
red), and an eye with no lid margin over or under it is refused (eyes.eye_depth).

Shapes made here: a face as a height field (a curved front, a nose, two sunken lid openings with steep walls and a
flat painted floor, an iris and a pupil painted on each floor), its paint a small picture; a sphere with rings of UV
standing in for ICT-FaceKit's eyeball; a small photo of two irises on skin with a pupil and a highlight.

The hair, on a toy painted head (a ball, its top half pushed out as a hair shell and painted dark, a nose, a body
under it in a coat's colour): the labels cover the painted top and nothing else; the scalp leaves no hole over the
hair, stays under its shell and meets the skin at its edge; the strands root on the scalp, stay out of the head and
reach into the shell; a darker colour gets more melanin and a grey head white strands. Breaks that turn its rows red
(each applied once, seen red, reverted, 2026-11-26): every triangle hair whatever its neighbours
(`labels.HAIR_SHARE` 0: extra 119%); the scalp let out through the shell (`scalp.CLEAR_M` -0.03: 165 directions
through); the scalp tucked 6 mm under the skin (`scalp.TUCK_M` 0.006: a 5.7 mm step at its edge); the head's inside
let into the hair's volume (`volume.inside_of` and `volume.seen_from` saying nothing is inside the head: 32% of the
strands into it).

Round 3 of the hair (2026-11-27), each break applied once, seen red, reverted: the grey fit ignoring the spread
(`fibre.grey_fit` given none: white share 0.84 and melanin 0.96 for 0.7 and 0.6 on a made-up swatch table); the photo's
backdrop read by colour alone (`labels.CLOSEUP["smooth"]` unbounded: none of a silver bob as light as the backdrop
held); a hair-white bit the clothes' colours claim never a stray (`labels.over_clothes` saying nothing is over the
clothes: the forehead island 0% hair) or brows taken whatever their paint (`labels.BROWS_DARKER` -inf, round 2's
rule: 0%), or never (+inf: the dark brows 100% hair); the forehead rooted wherever the paint says
(`strands.FOREHEAD["deg"]` 0: roots 3 cm over the eyes).

Round 4 of the hair (2026-11-27), each break applied once, seen red, reverted: the redness left out of the fit
(`fibre.coloured_fit` giving redness 0: the warm dark head none); the neck's back not reaching the scalp's foot
(`scalp.nape_of` ignored: the tube's back at z -0.029, not -0.079); the forehead's floor under every style
(`strands.grows_here` always fringed: no roots 3 cm over the eyes with no fringe).

Round 13 of the hair (2026-11-28), the jaw's corner: the neck closed round a hole the hair step left in a neck's side
40 to 80 degrees from its front, and the scalp held to a jaw's corner standing 20% out under the ear, never to an ear
as far out over it. Breaks that turn these rows red (each applied once, seen red, reverted): the neck kept on its
back half alone (`scalp.neck_reach`: 0.0 of the hole's rays meet it); its back not held to the nape where nothing is
met (`scalp.NAPE_COS` 2: the back at z -0.0866, past the scalp's foot); the jaw never held (`scalp.EAR_LOWEST_M` 1 m,
or `scalp.JAW_OUT` 0: the jaw's directions left out of the scalp); the ear held as the jaw (`scalp.EAR_LOWEST_M`
-1 m: 51 directions held to the ear's skin).

Round 2 of the hair (2026-11-26): the skin at the hole's edge is laid onto the scalp (`scalp.laid`, over the toy with
its hair's foot raised 3 mm more into a lip, standing up to 11 mm); the layer runs from the scalp's side to the outer
surface of a 2 cm spherical shell (`volume.layered`); the grooves of a corrugated plane and the streaks painted 30
degrees off a plane's u axis are read as its flow (`flow.grooves`, `flow.streaks`); a picture of straight strands
reads straight and of strands waving 5 mm every 4 cm their wave (`curl.curl_of`); the roots fade into the skin over
4 mm, none on the chin, and a beard thins out to its edge under the chin (`strands.hairline_fade`, `grows_here`,
`beard.neck_kept`). Breaks that turn these rows red (each applied once, seen red, reverted): `scalp.laid` returning
the points unchanged (a 7.7 mm lip); the layer turned round (`volume.layered` giving 1 less it); the normals' tensor's
axes read largest first (`flow.tensor_axes`: the groove read across the grooves); the strands' way read across them
(`curl.strand_ways` less a quarter turn: neither picture right); `strands.FADE_M` 2 mm (full at 2 mm);
`strands.LOWEST_UNDER_EYES_M` 1 m (roots on the chin); `beard.NECK_UNDER_NOSE_M` 1 m (the beard's edge kept whole).

The head swap (`head_swap.py`), on a toy head (a squashed sphere with a nose, an ear and a bun) moved by a known
similarity (scale 0.3, a turn, a shift): it is found again from its points, exactly by the least-squares similarity
(which fits a turn, never a mirror, even onto the toy's mirror image) and to a millimetre (under the points' own
spacing) by the two-way trimmed ICP from a start 15% off in scale and 8 mm off in place, upright as the real starts
are, with a sixth of its points stray; the scan's best scale is read between its steps (the vertex of the parabola
through the least miss); the seam's weight is all body at the cut and none at the band's top; a UV triangle's texels
are those inside it; and the head-to-body matrix written for the glTF files moves a glTF point where the Blender
matrix moves it. Breaks that turn its rows red (each applied once, seen red, reverted, 2026-11-26): the rotation's
reflection guard dropped (`sign` left the identity: the mirror image fitted by a reflection); the scale read over the
target's spread, not the source's (`target_centred.var`); the ICP fitting every pair, not the kept share (`kept`
1.0: the strays pull the fit off); `lowest` returning the scanned step (0.26, not 0.257); `head_swap.eased` rising,
not falling, with height; `gltf_matrix`'s frame change applied on one side only (`blender_matrix @ to_blender`).
The seam: a head path that doubles back is laid along the body's path keeping its order, every target on the body
path, where each point's nearest body point does not (`head_swap.laid_path`); a ragged two-walled head band laid onto a
body cut edge 2 to 5 mm in front lays its outer wall's edge on the body's exactly and folds none of its faces
(`head_swap.seam_shifts`). Breaks that turn their rows red (each applied once, seen red, reverted, 2026-11-27): the
isotonic hold dropped (`isotonic` returning its values: the targets run back on the doubled leg); the outer wall not
chosen (`outer_paths` taking every edge: both walls joined into one path, the outer edge laid off the body's). A
cut just under the jaw meets the neck as one loop each side: the head's loop is laid all round the body's, once round
(`laid_path`'s `closing`). Break (applied once, seen red, reverted, 2026-11-27): the loop read as an open path
(`closing` 0: the isotonic fit pooled the head's loop onto the body path's ends, an older woman's edge 3.5% laid).

The skin, on a flat front painted with soft blobs and a photo of it under a known map: the photo is found from a start
4 px and 2% off to within a pixel (`skin.registered`); a shading that follows the normal is divided out, a highlight's
excess mostly pressed off and recoloured to the skin's, plain skin kept (`skin.shading`, `skin.gloss_free`); a point
wears the photo only facing forward, on the front, inside the photo's face and clear of the eye's floor, and the T-zone
holds the nose, not the cheek (`skin.grid_share`, `skin.point_shares`, `skin.tzone`). Breaks that turn its rows red
(each applied once, seen red, reverted, 2026-11-26): one search of half a millimetre (`skin.ROUNDS` (0.0005,): 8.7 px
off); no shading taken off (`skin.SHADING_RANGE` (1, 1)); no gloss pressed (`skin.GLOSS` left 1); every slope facing
(`skin.FACING` (-1, -0.5): the turned side wears the photo); every point on the front (`skin.VISIBLE_M` 1: the hidden
point wears it); no fade at the eye (`skin.EYE_CLEAR_M` below 0: the eye's floor wears it).

The lids (`lids.py`), on two spheres behind a flat face 4 mm in front of them, each opening an ellipse 13 mm tall over
a deep floor, the photo's 9 mm: the refined mesh keeps its area, leaves no crack and carries its UVs; the photo's
opening is read round each eye at its own scale and held inside the ball; after the reshape the opening's top and
bottom lie on the photo's, the lid's front LID_M over the eye just outside them and no lid point inside the eye; upper
lashes root just outside the margin and rise, lower ones fall, all leaving forward; a brow's hairs grow where its photo
is dark and lie on the skin; a painted brow is painted over with the skin round it. Breaks that turn their rows red
(each applied once, seen red, reverted, 2026-11-26): only the chosen triangles split, their neighbours not closed
(`lids.refined`); the corner hold dropped (`lids.photo_outline`); the lid's front 3 mm over the eye
(`lids.lid_profile`); the points not moved across (`lids.moved_across`); the lid let 3 mm into the eye
(`lids.reshaped`); the lashes' curl turned round (`lids.lid_lashes`); every brow place kept whatever the photo's
darkness (`lids.brow_hairs`); the brow left painted (`lids.unpainted`).

The whole head's run (`head.py`; 2026-11-26, round 1): a photo's iris (MediaPipe's circle 15% wide, a catchlight on
it) is unrolled onto the eyeball's UV with its pupil at the photo's share, no reflection left in the iris and the
white outside it (`eyes.iris_picture`); a photo with dense lashes gets the full lashes and one with a few fewer
(`lids.lash_share`); the paint's dark baked band is lifted to the skin round it, plain skin and dark hair left
(`skin.paint_shade`); a painted brow wearing the photo is skin (`skin.skin_triangles`). Breaks that turn their rows
red (each applied once, seen red, reverted): MediaPipe's iris circle taken as it is (`eyes.iris_found`: the pupil
read at 0.26); no reflection taken off and no detail clipped (`eyes.IRIS_PICTURE` catchlight 100, detail (0, 10):
the reflection ten times the iris); every photo full of lashes (`lids.LASH_PHOTO` full 0.01); no lift
(`skin.PAINT_SHADE` gain 1); the photo's share ignored (`skin.skin_triangles` with no shares: the brow left).
Round 2 (2026-11-26): a point on a steep side is on the front (`skin.visible`); the paint on the skin is given the
photo skin's mean and spread, the hair left (`skin.paint_toned`); a hidden layer stays behind the face the lid's
move pulls forward (`lids.layers_kept`). Breaks that turn their rows red (each applied once, seen red, reverted):
no slope allowance (`skin.VISIBLE_SLOPE` 0: the steep point is paint); no broad scale (`paint_toned`'s
`broad_scale` 1: the rust patch and shade band keep their spread); the mask ignored (every texel toned: the hair
too); nothing hidden (`lids.LAYERS` hidden_m 1: the hidden layer pulled onto the face).
Round 3 (2026-11-27): a hollow the model's front shuts reads shut and the photo's darker, warmer light in it is
divided out per channel (`skin.occlusion`, `skin.shading`); the photo's fringe (strands with skin between, from the
top edge) and lid openings are left out of its face, its brows and a moustache under the pupils kept
(`skin.face_mask`, `skin.eye_openings`); the model's painted fringe wears no photo, its beard's middle may
(`skin.model_hair_free`); the share rises over EDGE_FEATHER_M from its outer edge (`skin.grid_share`). Breaks that
turn their rows red (each applied once, seen red, reverted): the old clip (`skin.SHADING_RANGE` (0.8, 1.25): the
hollow kept its shade); no occlusion term (`occlusion` all 0); every place hair (`skin.hair_zone` always true: the
moustache left out); no hair taken out (`hair` none: the fringe kept); no lid openings (`EYE_GROW_M` and the polygon
dropped); no feather (`EDGE_FEATHER_M` 1e-9: the edge at full share).
A bearded man wears the photo's own beard (b_hoodie_man, 2026-11-28): where its lightness spreads (hairs against the
skin between them) and it is coloured, under the pupils (`skin.hair_share`), with the skin it closes round, joined to
the face (`skin.photo_beard`), and his model's painted cheeks are no head hair (`skin.model_hair_free` with `beard`).
Breaks that turn its row red (each applied once, seen red, reverted): no chroma bar (`skin.BEARD` chroma 0: the
hood's grey folds joined); no texture bar (`texture` (0, 1e-6): the shaded cheek is beard); the beard's rows still
head hair (`hair_zone`'s `beard_under` ignored).

The cloth (`cloth.py`), on toys: a grid painted jacket over jeans with a fleck of T-shirt and stray jeans faces in the
jacket comes out clean after the vote and the islands; a tube's distance over its surface from its top loop is its
height under it, so the jeans ride a waistband's width; a walk whose last frame repeats its first is a cycle a frame
shorter and its travel carries on cycle after cycle; the body under the clothes is pushed in to the margin under a
close shell and not at all under a far one. Breaks that turn its rows red (each applied once, seen red, reverted,
2026-11-26): no islands joined (`cloth.ISLAND_FACES` 0: 2 stray faces); the distance counted in edges, not metres
(`over_surface` lengths all 1); no closed cycle seen (`cloth.CLOSED_DEGREES` 0: 5 frames a cycle); the push read
the wrong way (`margin + over` in `cloth.pushes`).
The sim mesh (`cloth_mesh.py`), on toys: a body column inside a two-walled open garment tube with a sliver and a speck
is laid onto the inner wall as one manifold piece whose only rims are the tube's two ends; a needle left in a grid is
collapsed and two triangles meeting at a point are made two fans; points bound over and under a bent sheet come back
exactly at rest and are carried rigidly when it turns and moves, and a piece of mesh with no riding point rides
whole. Breaks that turn their rows red (each applied once, seen red, reverted, 2026-11-26): the last hit taken for
the first (`laid_over`'s `first`: the outer wall); no collapse rounds (`slivers_collapsed` rounds 0); no extra fan
(`fans_split`'s `extra` empty); the offset added unturned (`carried` without its frame); `anchored` returning
`riding` alone. Round 4 (2026-11-27), each applied once, seen red, reverted: the normals unturned (`skinned_normals`
returning its normals: the cloth shaded as it stood); the drawn surface not moved off its skinned place (`displaced`
returning zeros); the jacket allowed on a leg (`allowed` without `LEGS`: the shards
at the hem). Round 5 (2026-11-27), each applied once, seen red, reverted: a long coat's hem read off every face of a
band (`outer_share` the plain share: the hem stays at its start, 0.9 m); the scarf needing to stand 1 m forward
(`SCARF_FORWARD_M` 1.0: no scarf found); the paint read at the file's places as stored (`file_places` returning its
places: the top's red read as the bottom's blue); the under body's sRGB left unlinearised (`under_colours`: the
jacket's grey 0.5, not 0.214). Cloth round 5 (2026-11-27), each applied once, seen red, reverted: no skirt (`skirted`'s
share 0: the coat's middle on one thigh); `SHORT_LEAST` 0 (the 1 mm edge kept). Round 5's sleeve cut and its cover
went in cloth round 6 (they tore the drawn jackets), and their row with them. Cloth round 6, applied once, seen
red, reverted: `SKIRT_ARM_EASE_M` 1e-6 (the point 2 cm from a resting hand skirted whole, 0.54).

The colour (`colour.py`), on a toy front (a jacket painted dark grey-green with darker fold stripes over trousers
painted black, boots at the bottom painted as black as the trousers with a trace of red) and its photo (a sage
jacket with no stripes, navy trousers, brown boots): after toning, the jacket, trousers and boots each read within a
few Lab units of the photo's, and the jacket's painted folds keep most of their depth. Breaks that turn its rows red
(each applied once, seen red, reverted, 2026-11-26): no height in the clusters (`colour.HEIGHT_LAB` 0: the boots
fall in with the trousers and miss their brown); each cluster its own move (`colour.merged` and `garments` giving every
cluster its own garment: the fold stripes flattened to the photo's plain jacket); no spread kept
(`colour.SPREAD_RANGE` (0, 0): the folds gone). On a toy bust (dark hair on top, a face painted skin in its left
half and dark in its right, the hollow head's back seen through it, over a jacket painted dark grey-green; its photo
dark hair, a light skin face and a sage jacket), the hair and both face halves keep their paint within 2 Lab units and
the jacket still moves to within 6 of the photo's. Break that turns its row red (applied once, seen red, reverted,
2026-11-26): no body kept (`colour.bodily` all False: the face's two halves joined into one garment and moved to the
photo's skin, the dark half cream, as on b_hoodie_man's head). A swapped model (its head and body two primitives, each
on its own picture) is toned through the file: each picture keeps its size and each half's jacket reaches the photo's
sage. Break that turns its row red (applied once, seen red, reverted, 2026-11-26): the model read through trimesh's
`force="mesh"` (the old `model_of`: one 512 x 256 atlas written over the first picture, both jackets off the sage).

The tethered cloth (`cloth_tether.py`), on a curtain swung toward and away from a ball behind it, its top row riding,
feeling g toward the ball: the riding row stays on its targets, every point within its tether, none deeper toward the
ball than its target or the clearance, the loose cloth hangs over a centimetre off its targets and no edge stretches
past 5%; the gravity felt beyond the rest hang is none unturned, g times the square root of two turned a quarter and
twice g turned over; round a box body a point is inside only where all its nearest body points' planes say so. Breaks
that turn their rows red (each applied once, seen red, reverted, 2026-11-27): no retraction (`retracted` returning its
positions: the curtain into the ball past its target); one plane asked (`NEIGHBOURS` 1: 48 outside points pushed); the
whole of g felt (`turned_gravity` returning GRAVITY).

The whole person (`person.py`): the hair step's removed triangles are read back from kept.glb's faces, and a body
thinned to a third and moved by a known similarity is framed again from a start 5% and 3 cm off. Breaks that turn
their rows red (each applied once, seen red, reverted, 2026-11-27): the kept faces' keys read in another order
(`removed_faces` keying kept by its corners reversed: every face removed); the fit's scale held (`framed` with
`free_scale` False: the scale stays 5% off). And head.glb wears the skin step's paint as written (`head.paint_picture`;
break: encoded again by `head.picture`, 0.5 written as 188, the washed paint the whole person's first render showed).
The chin over the cut (`head_swap.chin_over_cut`, from which up the whole face rides the Head rigidly) is the lowest
slice of the face's middle column standing 2.5 cm forward of the throat; a column with no chin is refused. Breaks
(each applied once, seen red, reverted, 2026-11-27): the column's width left out (the shoulder read as the chin, 0.005);
the throat read as the column's highest slice (no chin found, the row's refusal raised).
The cut's level is read off the swapped head (`head_swap.chin_under_crown`: the first slice of the face's middle
column 2.5 cm behind the nose's front), the hood keeps the chin the head's (`kept_region`'s `chin`) and a cut that
took the chin is refused (`chin_whole`). Breaks (each applied once, seen red, reverted, 2026-11-27): the chin read as
the first 1.5 cm drop from one slice to the next (the nose's underside read as the chin); the hood's chin clause left out
(the chin under the hood's depth given to the neck's reach and dropped: the stairwell woman's torn lower lip). The
face's middle column runs through the nose's tip (`head_swap.face_column`), never the body's axis, and the hood keeps
the chin within the column's reach from the chin's bottom to the hood (`face_reach`). Break (applied once, seen red,
reverted, 2026-11-28): the column on the body's axis (a face 3.4 cm off it read on the chin's side, its front 0.045,
the chin dropped: the stairwell woman's torn chin under her lower lip).
A scarf rides from where it meets anything over the chest (`cloth.riding_of`, `cloth.borders` reading each face pair
both ways). Breaks (each applied once, seen red, reverted, 2026-11-27): the scarf's border read off the head and
skin alone, and `borders` reading each pair one way (the turtleneck's collar met at no point: the scarf rode whole).
Round 14 (2026-11-28): JAW_BAND under the hood's depth the head keeps its faces within the face's reach all round
(`head_swap.kept_region`; the stairwell woman's hood at 0.125 cut her jaw's corner, whose skin reaches 0.132, and
its open edge showed the neck tube as a dark red flap), and the neck tube runs all round under the skin from
`scalp.JAW_KEPT_M` under the eyes down (kept in front only where nothing was met, its far side showed under her jaw
as a dark red line). Breaks (each applied once, seen red, reverted): JAW_BAND 0; JAW_KEPT_M 1 m.
Under the hood's depth the head model keeps only its neck (`head_swap.kept_region`): its throat in front kept, a chin's
underside turned down kept, its own collar standing 10 cm out in front and at the side given to the body, a face
inside a neck ring turned in refused. Break (applied once, seen red, reverted, 2026-11-27): the front kept whole
again (the head's front collar kept: the stairwell woman's torn collar shards). Under a hood open in front (a
hoodie's, `open_front`) the whole front is the head's down to the cut, its side still the body's. Break: `open_front`
ignored (the hoodie man's chin and beard given to the body, whose own longer beard stood under his face as a dark
lump).
The T-shirt, the garment under the jacket, may show round the neck off the arms (`cloth.allowed`, ROUND_NECK_M: a
hoodie's hood). Break: `round_neck` left out (the hoodie man's grey hood read as the jacket, torn on its sim mesh).
The jeans' own points ride no arm (`cloth.jeans_off_arms`). Break: the call left out of `made` and the row's
zeroing skipped (the hoodie man's jeans fused to his hands ballooned out at the hips as his arms were kept out).
A face no kind's place allows takes the nearest paint's kind (`cloth.kinds_of`). Break: the `nowhere` fill left
out (argmin over no allowed kind gave the head: the hoodie man's trousers fused to his forearms drawn as wedges).
The beard takes the mouth's piece under the lower lip down to the chin (`beard.holes_in`, LIP_UNDER_NOSE_M). Break:
the `chin` term left out (the hoodie man's pale chin lumps, joined to his lips, showed bare under his beard).
An arm's face under the jacket's hem within LEG_FUSED_M of a thigh's is the trousers (`cloth.fused_to_leg`). Break
(applied once, seen red, reverted, 2026-11-28): LEG_FUSED_M 0.2 (the hand held out beside the thigh taken too).
A jacket piece wholly round the neck and bordered by the T-shirt kind is the hood's (`cloth.hood_inside`). Break
(applied once, seen red, reverted, 2026-11-28): the `outside` term left out (the collar reaching down taken too).
A beard is as dense as its style's `beard_density_m2` (`beard.beard_strands`). Break (applied once, seen red,
reverted, 2026-11-28): the style's density unread (beard.DENSITY alone: ratio 1.0).
A jeans hem resting on a shoe turns with the foot (`cloth.hem_on_shoes`). Break (applied once, seen red, reverted,
2026-11-27): HEM_SHOE_M 0 (the hem left on the shin, sliding in and out of the shoe).
A garment's seam to a skinned kind takes none of the cloth's move (`cloth.seam_eased`). Break (applied once, seen
red, reverted, 2026-11-28): SEAM_EASE_M 1e-9 (the seam moved in full: the jeans stood off the shoes and the puffer
off its own neck by up to 1.5 cm, ragged hems and a torn collar top).
A cloth garment's weights are smoothed over its own surface (`cloth.weights_smoothed`). Break (applied once, seen
red, reverted, 2026-11-28): WEIGHT_SMOOTH_ROUNDS 0 (the foot's speckled share tore the hems into fins at each stride).
still_rig's fan across the cut's loop (`person.neck_fans`) is found, the neck tube and a fan far under the cut kept.
Breaks (each applied once, seen red, reverted, 2026-11-27): `FAN_BAND` 1 (the armpit's fan taken too); `FAN_OFF_M` 1
with `FAN_MIDDLE_M` 1 (no cut fan found); `FAN_MIDDLE_M` 1 (the wedge reaching out over the band kept); 2026-11-28:
`FAN_SHARED` 10**9 (8 of the collar fan's 26 faces, those along the tube,
kept: the stairwell woman's pleated neck). The head's open edge at the cut is hung with a skirt (`head_swap.skirt`).
Break (applied once, seen red, reverted, 2026-11-28): the skirt's triangles turned as the edge (first, second,
copy), not as its neighbour (half the skirt facing in, drawn from inside as dark wedges).
The Head's share on the body's neck under the cut is moved down the neck chain by height (`person.neck_chained`).
Breaks (each applied once, seen red, reverted, 2026-11-28): the Head's share kept (`moved` 0: the stairwell woman's
front neck hung 0.42 from the Head under the Neck1 joint and folded into pale shards as she walked); NECK_UNDER
1e-9 (the share taken off all at once at the cut: the rig's neck left the head's skirt and showed through it).
The rig's faces round the neck by
where they came from (`person.neck_roles`): the body's own collar over the cut released, the head's neck and the body
far under the cut not; the head's faces on its hair read as the hair, those on its skin not. Breaks (each applied
once, seen red, reverted, 2026-11-27): `RELEASE_BAND` 1 (the body far under the cut released); `HAIR_ON_M` 0 (the face
on the hair not read). Faces round the neck released from still_rig's head part take their kind by paint
(`cloth.kinds_of`): one painted as the jacket the jacket, one as the skin the skin (skin's place or not), one as the
hair the head, one never released the head. Breaks (each applied once, seen red, reverted, 2026-11-27): `released`
left out of the head's mask (all four the head); the skin's place kept (the released skin face the jacket); no hair
read (the old hair the jacket); the skin's anywhere for every released face (the shoulder's scarf the skin, whole
person round 7: brown blotches on the older woman's scarf). That old hair is painted over as the kind it lies on (`cloth.painted_over`: taken
off, it opened the collar's top over its black hollow), its own points weighted as that kind's nearest point. Breaks
(each applied once, seen red, reverted, 2026-11-27): the head kept as a target (the second old hair the head); the
weights left as they were. Drawn, the old hair's own texels are painted again with the garment's paint at their
nearest points on it (`painted.repainted`), every texel a bilinear read of a triangle reaches, and only paint like the
garment's (`painted.kind_like`). Breaks (each applied once, seen red, reverted, 2026-11-28): the donor triangle's
first corner read for the whole triangle (a flat paint); TEXEL_REACH 0 (the tiny triangle given none); LIKE_SPREADS
100 (the dark read). The skin's matte is read over plain skin (`skin.plain_skin`) and a socket's shade deeper than the
fitted line is taken off (`skin.hollows`), a stain on open skin kept. Breaks (each applied once, seen red, reverted,
2026-11-27): `skin.MATTE_DARK` 0 (the skin between a brow and the lashes pressed as a highlight); `skin.HOLLOW`'s
`shut` (5, 6) (the socket left 18% dark); `shut` (-2, -1) with `MATTE_DARK` 0 (the stain lifted).
The body's own neck under the cut takes the head's skin (`head_swap.neck_move`, `neck_share`, `skin_like`,
`stubble_carried`, `seam_offsets`; the hoodie man's neck a flat pink slab under his photo's skin, 2026-11-28): its
pink paint moved in Lab onto the photo's skin median, its spread never widened; the move whole under the cut, eased out
down the neck and over the head's paint band; a neck's paint is skin, a white scarf's or a black collar's not; the
head's stubble share carried down the neck; the seam's colour whole on the head's skin, none past its fade. Breaks
(each applied once, seen red, reverted, 2026-11-28): NECK_SPREAD (0.67, 1.5) (the paint's blotches widened);
`neck_share` 0 under the cut (the neck left pink); SKIN_CHROMA 0 (the white scarf read as skin).
The neck is toned to the photo's skin over the lower face, not under the jaw (`head_swap.photo_on_face`; the light fit
lifted the hoodie man's under-jaw to L 76 against his face's 60, 2026-11-28), the skirt's copies land on the body's
neck within reach (`landed`), and the body's neck is cut level under the head (`level_plane`). Breaks (each applied
once, seen red, reverted, 2026-11-28): NECK_FACE_BAND (0, 0.02) (the under-jaw read); `landed` with no reach (the far
copy dragged 3 cm); `level_plane`'s normal negated (the plane's up turned down).

The strands laid on and over the cloth (`over_cloth.laid_over`; the stairwell woman's hair through her puffer collar,
2026-11-28): strands hanging down through a sloped plate wound face down (a two-sided garment's normal points either
way) lie on its top CLEAR_M off it with their steps' lengths kept, slide off its low edge, and a strand beside it is
not moved. Breaks that turn the row red (each applied once, seen red, reverted, 2026-11-28): the side read off the
face's normal alone (`slid`'s side 1: the hair pushed through to the plate's underside); the voxel reach without the
step (`voxel_size` of the edges alone: the crossing steps never looked at); the length not kept (`slid`'s
keep_length dropped: steps shortened on the plate).
"""
import functools
import types

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

from tools.characters.generated import (__main__, beard, cloth, cloth_tether, colour, curl, eyes, fibre, flow,
                                        head, head_swap, labels, lids, over_cloth, painted, person, scalp, skin,
                                        strands, volume)
from tools.characters.whole import hair

NOSE_Y = 0.06
EYES_OVER_NOSE = 0.037
EYES_APART = 0.064
OPENING_M = (0.013, 0.006)  # half width and half height of each lid opening
SOCKET_DEPTH_M = 0.006
WALL_SHARE = 0.8  # the opening's wall rises from this share of its size to its edge
SKIN = (0.8, 0.6, 0.5)
PAINTED_IRIS = (0.3, 0.2, 0.1)


def spaced(low, high, fine_low, fine_high, fine, coarse):
    """Grid lines from low to high, `fine` apart between fine_low and fine_high and `coarse` apart elsewhere."""
    return np.unique(np.concatenate([np.arange(low, high + 1e-9, coarse), np.arange(fine_low, fine_high, fine)]))


def opening_share(x, y):
    """Each point's place in the nearer lid opening: 0 at its middle, 1 on its edge."""
    shares = [np.hypot((x - side * EYES_APART / 2) / OPENING_M[0], (y - NOSE_Y - EYES_OVER_NOSE) / OPENING_M[1])
              for side in (-1, 1)]
    return np.min(shares, axis=0)


def front_of(x, y):
    """The face's depth without its sockets: a curved front and a nose."""
    return 0.10 - 3.0 * x ** 2 + 0.025 * np.exp(-0.5 * ((x / 0.008) ** 2 + ((y - NOSE_Y) / 0.008) ** 2))


def surface(x, y):
    """The face's depth: its front with two sockets sunk SOCKET_DEPTH_M inside steep walls."""
    front = front_of(x, y)
    sunk = np.clip((1.0 - opening_share(x, y)) / (1.0 - WALL_SHARE), 0.0, 1.0)
    return front - SOCKET_DEPTH_M * sunk


@functools.lru_cache(maxsize=None)
def face():
    """The height-field face: (points, triangles, uv, texture), y up, looking along +z, its top at 0.24 m."""
    eye_y = NOSE_Y + EYES_OVER_NOSE
    xs = spaced(-0.075, 0.075, -0.05, 0.05, 0.0004, 0.002)
    ys = spaced(0.0, 0.24, eye_y - 0.012, eye_y + 0.012, 0.0004, 0.002)
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel(), surface(grid_x, grid_y).ravel()])
    width = len(xs)
    corner = (np.arange(len(ys) - 1)[:, None] * width + np.arange(width - 1)[None, :]).ravel()
    triangles = np.vstack([np.column_stack([corner, corner + 1, corner + width + 1]),
                           np.column_stack([corner, corner + width + 1, corner + width])])
    uv = np.column_stack([(points[:, 0] + 0.075) / 0.15, points[:, 1] / 0.24])
    rows, cols = np.mgrid[:600, :600]
    paint_x, paint_y = cols / 599 * 0.15 - 0.075, (599 - rows) / 599 * 0.24
    texture = np.ones((600, 600, 3)) * SKIN
    for side in (-1, 1):
        out = np.hypot(paint_x - side * EYES_APART / 2, paint_y - eye_y)
        texture[out < 0.00585] = PAINTED_IRIS
        texture[out < 0.002] = 0.02
    return points, triangles, uv, texture


def photo(iris):
    """A 400 px photo of two irises of sRGB colour `iris` on skin, each with its white, pupil and highlight."""
    picture = np.ones((400, 400, 3)) * (0.78, 0.66, 0.6)
    rows, cols = np.mgrid[:400, :400]
    for col in (170, 230):
        white = np.hypot((cols - col) / 2.2, rows - 160) < 6.5
        out = np.hypot(cols - col, rows - 160)
        picture[white] = (0.85, 0.82, 0.8)
        picture[out < 5.6] = iris
        picture[out < 2.0] = 0.02
        picture[np.hypot(cols - col - 2, rows - 158) < 1.0] = 1.0
    return picture


def face_module_iris_uv():
    """The face module's iris ring on the eyeball's UV."""
    return eyes.face_modules()[0].IRIS_UV


def sphere_eye():
    """A stand-in for ICT-FaceKit's eyeball (cm): a sphere looking along +z, its UV in rings out from its front."""
    ball = trimesh.creation.icosphere(subdivisions=4, radius=1.2)
    points = np.asarray(ball.vertices)
    theta = np.arccos(np.clip(points[:, 2] / 1.2, -1, 1))
    phi = np.arctan2(points[:, 1], points[:, 0])
    out = face_module_iris_uv() * theta / np.radians(28.0)  # the iris's edge 28 degrees off the front, as on ICT's eye
    point_uv = 0.5 + out[:, None] * np.column_stack([np.cos(phi), np.sin(phi)])
    triangles = np.asarray(ball.faces)
    eye = {"points": points, "triangles": triangles, "uv": point_uv[triangles]}
    face_module, _ = eyes.face_modules()
    return {**eye, "finish": face_module.eye_finish(eye["uv"]), "centre": np.zeros(3), "axis": np.array([0, 0, 1.0]),
            "radius": 1.2}


@functools.lru_cache(maxsize=None)
def made():
    """The eyes made on the height-field face with brown irises in its photo."""
    points, triangles, uv, texture = face()
    return eyes.made(points, triangles, uv, texture, photo((0.36, 0.2, 0.12)),
                     {"right": sphere_eye(), "left": sphere_eye()})


def pupils_found():
    """Each found pupil within half a millimetre of its painted one."""
    found = np.array(made()["stats"]["pupils_m"])
    painted = np.array([[-EYES_APART / 2, NOSE_Y + EYES_OVER_NOSE], [EYES_APART / 2, NOSE_Y + EYES_OVER_NOSE]])
    return (np.linalg.norm(found - painted, axis=1) < 0.0005).tolist()


def behind_lids():
    """Whether the ball, where it rests before EYE_FORWARD_M moves it forward, is behind every lid margin over and
    under the pupil (by at least RIM_GAP_M less a tenth of a millimetre) and its cornea's apex behind the opening's rim
    but within 2 mm of it."""
    result = made()
    centres = np.array(result["stats"]["eye_centres_m"])
    radius = result["stats"]["eye_diameter_mm"] / 2000.0
    gaps, apexes = [], []
    for centre in centres:
        angles = np.radians(np.r_[np.arange(45, 140, 10), np.arange(225, 320, 10)])
        edge = 1.0 / np.sqrt(np.cos(angles) ** 2 / OPENING_M[0] ** 2 + np.sin(angles) ** 2 / OPENING_M[1] ** 2)
        x, y = centre[0] + edge * np.cos(angles), centre[1] + edge * np.sin(angles)
        margin = surface(x, y)
        resting = centre[2] - eyes.EYE_FORWARD_M
        gaps.append(margin - (resting + np.sqrt(radius ** 2 - edge ** 2)))
        apexes.append(margin.mean() - (resting + radius * (1 + eyes.CORNEA_RISE)))
    return [bool(np.min(gaps) > eyes.RIM_GAP_M - 0.0001), bool(0.0 < np.min(apexes) < 0.002)]


def floor_removed():
    """Whether every removed triangle lies inside the opening and the floor under each pupil is removed."""
    removed = made()["removed"]
    if not len(removed):
        return [True, False]
    inside = opening_share(removed[:, 0], removed[:, 1]) < 1.0
    under = [np.min(np.hypot(removed[:, 0] - side * EYES_APART / 2, removed[:, 1] - NOSE_Y - EYES_OVER_NOSE)) < 0.001
             for side in (-1, 1)]
    return [bool(inside.all()), all(under)]


def floor_pushed_lids_kept():
    """Whether every pushed point lay inside an opening at least LID_EDGE_M (less 0.2 mm, the margin found a little
    under the front's top) behind the face's front, so no lid moved, and went straight back (never forward or
    sideways), the floor beside the ball now as deep as the ball's middle (within the stats' rounding)."""
    result = made()
    start, end = result["moved_from"], result["moved_to"]
    centres = np.array(result["stats"]["eye_centres_m"])
    radius = result["stats"]["eye_diameter_mm"] / 2000.0
    on_floor = ((opening_share(start[:, 0], start[:, 1]) < 1.0)
                & (front_of(start[:, 0], start[:, 1]) - start[:, 2] > eyes.LID_EDGE_M - 0.0002))
    straight_back = np.allclose(start[:, :2], end[:, :2]) and bool((end[:, 2] <= start[:, 2]).all())
    across = np.min([np.hypot(end[:, 0] - centre[0], end[:, 1] - centre[1]) for centre in centres], axis=0)
    beside = across >= radius
    shaded = bool((end[beside, 2] <= centres[:, 2].max() + 1e-5).all())
    return [bool(on_floor.all()), straight_back, shaded, bool(len(start) > 0)]


def wet_line_on_rims():
    """Whether the wet line lies on the lids' inner rims (each triangle's centre inside or by an opening's edge and no
    deeper than a millimetre past LID_EDGE_M behind the face's front there) and runs round both eyes."""
    strip = made()["wet"]
    wet = strip["points"][strip["triangles"]].mean(axis=1)
    near_edge = opening_share(wet[:, 0], wet[:, 1]) <= 1.1
    below_front = front_of(wet[:, 0], wet[:, 1]) - wet[:, 2]
    on_rim = (below_front > -0.0002) & (below_front < eyes.LID_EDGE_M + 0.001)
    sides = {int(np.sign(x)) for x in wet[:, 0]}
    return [bool(near_edge.all()), bool(on_rim.all()), sides == {-1, 1}]


def gaze_agrees():
    """Whether both eyes' pupils (the eyeball's pupil finish) look at one point, straight ahead within a degree."""
    result = made()
    eye_points, centres = result["eyes"], np.array(result["stats"]["eye_centres_m"])
    pupil_triangles = eye_points["triangles"][eye_points["finish"] == 2]
    pupil_points = eye_points["points"][pupil_triangles].mean(axis=1)
    looks = []
    for centre in centres:
        own = pupil_points[np.linalg.norm(pupil_points - centre, axis=1) < 0.02]
        way = own.mean(axis=0) - centre
        looks.append(way / np.linalg.norm(way))
    target = np.array([centres[:, 0].mean(), centres[:, 1].mean(), centres[:, 2].max() + eyes.GAZE_M])
    aimed = [np.degrees(np.arccos(np.clip(look @ ((target - centre) / np.linalg.norm(target - centre)), -1, 1)))
             for look, centre in zip(looks, centres)]
    return bool(max(aimed) < 1.0)


def iris_read(srgb):
    """Whether the photo's iris colour is read within a tenth of its own (linear), the pupil and highlight left out."""
    colour, _, _ = eyes.photo_iris(photo(srgb))
    wanted = eyes.srgb_to_linear(srgb)
    return bool(np.all(np.abs(colour - wanted) <= 0.1 * wanted + 0.002))


def margins_read():
    """Where margin_along puts the lid on three rays out from a pupil (millimetres out, the ray sampled every
    STEP_M): a steep lid at 6 mm, a gentle one (rising 2 mm over 3.5 mm) ending at 9 mm, and a steep lid at 8 mm
    behind a 1.2 mm bump on the floor at 4 mm; and nothing along a floor that only curves up slowly."""
    out = np.arange(0.0, 0.014, eyes.STEP_M)
    steep = np.clip((out - 0.005) / 0.001, 0.0, 1.0) * 0.005
    gentle = np.clip((out - 0.0055) / 0.0035, 0.0, 1.0) * 0.002
    bumped = 0.0012 * np.exp(-0.5 * ((out - 0.004) / 0.0004) ** 2) + np.clip((out - 0.007) / 0.001, 0, 1) * 0.005
    curved = 0.19 * out
    found = [eyes.margin_along(depth, 1.0, 0.0) for depth in (steep, gentle, bumped, curved)]
    return [None if index is None else round(out[index] * 1000) for index in found]


def lidless_refused():
    """An eye with lid margins only beside it (none over or under) is refused."""
    margins = np.array([[0.012, 0.0, 0.1, 0.0], [-0.012, 0.0, 0.1, 180.0]])
    try:
        eyes.eye_depth(np.zeros(2), margins, 0.012)
    except ValueError:
        return "refused"
    return "placed"


HEAD = np.array([0.0, 1.6, 0.0])
RADIUS = 0.09
SHELL_M = 0.015
COLOURS = {"hair": (8.0, 2.0, 3.0), "skin": (70.0, 15.0, 24.0), "coat": (40.0, -5.0, 0.0)}


@functools.lru_cache(maxsize=1)
def toy():
    """(points, faces, Lab colour per face, hair truth per face, frame)."""
    ball = trimesh.creation.icosphere(subdivisions=4, radius=RADIUS)
    points = np.asarray(ball.vertices).copy()
    up = points[:, 1] / RADIUS
    front = points[:, 2] / RADIUS
    cap = np.clip((up - 0.05) / 0.15, 0.0, 1.0) * (front < 0.75)
    points += points / RADIUS * (SHELL_M * cap)[:, None]
    nose = np.exp(-((points[:, 0] / 0.015) ** 2 + ((points[:, 1] + 0.035) / 0.02) ** 2)) * (front > 0.0)
    points[:, 2] += 0.02 * nose
    points += HEAD
    body = trimesh.creation.cylinder(radius=0.16, height=0.45)
    body.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
    body.apply_translation([0.0, 1.6 - RADIUS - 0.04 - 0.225, 0.0])
    body = body.subdivide().subdivide()
    faces = np.vstack([np.asarray(ball.faces), np.asarray(body.faces) + len(points)])
    points = np.vstack([points, np.asarray(body.vertices)])
    truth = np.zeros(len(faces), dtype=bool)
    truth[:len(ball.faces)] = cap[np.asarray(ball.faces)].mean(axis=1) > 0.5
    colours = np.tile(COLOURS["skin"], (len(faces), 1))
    colours[truth] = COLOURS["hair"]
    colours[len(ball.faces):] = COLOURS["coat"]
    colours += np.random.default_rng(1).normal(0.0, 1.0, colours.shape)
    return points, faces, colours, truth, labels.head_frame(points, faces, colours)


def labelled():
    points, faces, colours, _, frame = toy()
    return labels.hair_labels(points, faces, colours, frame, False, 0.3)[0]


def labels_hold():
    found, truth = labelled(), toy()[3]
    missed = (truth & ~found).sum() / truth.sum()
    extra = (found & ~truth).sum() / truth.sum()
    return missed < 0.05 and extra < 0.05, f"missed {missed:.3f}, extra {extra:.3f}"


def scalp_closes():
    points, faces, _, _, frame = toy()
    hair_faces = labelled()
    patch = scalp.scalp_patch(points, faces, hair_faces, frame)
    start = scalp.origin(frame)
    directions = trimesh.creation.icosphere(subdivisions=3).vertices
    over_hair = directions[(directions[:, 1] > 0.35) & (directions[:, 2] < 0.5)]
    shell = scalp.first_hit(points, faces[hair_faces], start, over_hair)
    under = scalp.first_hit(patch["points"], patch["triangles"], start, over_hair)
    holes = int((~np.isfinite(under)).sum())
    through = int((under > shell - 0.001).sum())
    skin = trimesh.Trimesh(points, faces[~hair_faces], process=False)
    seam = patch["points"][~patch["hole"]]
    step = float(np.percentile(skin.nearest.on_surface(seam)[1], 95))
    return holes == 0 and through == 0 and step < 0.002, f"holes {holes}, through {through}, step {step * 1000:.2f} mm"


def strands_fill():
    """The strands, at a fortieth of a head's density from 1500 guides (the toy's size, not the route's)."""
    saved = hair.DENSITY, strands.GUIDES, strands.CANDIDATES
    hair.DENSITY = {key: value / 40.0 for key, value in saved[0].items()}
    strands.GUIDES, strands.CANDIDATES = 1500, 40000
    try:
        return strands_measured()
    finally:
        hair.DENSITY, strands.GUIDES, strands.CANDIDATES = saved


def strands_measured():
    points, faces, colours, _, frame = toy()
    hair_faces = labelled()
    patch = scalp.scalp_patch(points, faces, hair_faces, frame)
    body = __main__.body_of(points, faces, hair_faces, patch, None, frame)
    model, model_labels = __main__.model_near_hair(points, faces, hair_faces)
    space = volume.hair_volume(model, model_labels, body, np.random.default_rng(2), scalp.origin(frame))
    style = {"length_m": 0.3, "wave_m": 0.001, "wave_period_m": 0.05, "parting": "none", "fringe_side": "none"}
    skin_like = labels.skin_like(colours)
    hairline = __main__.hairline_of(points, faces, hair_faces, skin_like, frame)
    field = flow.flow_field(points, faces, np.zeros((len(points), 2)), np.zeros((4, 4, 3), np.uint8), hair_faces,
                            space)
    counts, strand_points, _ = strands.regrown(space, field, patch, (points, faces[~hair_faces & skin_like]),
                                               hairline, frame, style)
    each = strand_points.reshape(len(counts), -1, 3)
    roots_off = trimesh.Trimesh(patch["points"], patch["triangles"]).nearest.on_surface(each[:, 0])[1]
    into = np.linalg.norm(each - HEAD, axis=2).min(axis=1) < RADIUS - 0.004
    reach = np.linalg.norm(each[:, -1] - each[:, 0], axis=1)
    return (np.percentile(roots_off, 99) < 0.002 and into.mean() < 0.01 and np.median(reach) > 0.02,
            f"roots off {np.percentile(roots_off, 99) * 1000:.2f} mm, into {into.mean():.3f}, "
            f"reach {np.median(reach) * 1000:.1f} mm")


def neck_toy(window):
    """A 10 cm neck of skin 15 cm under the eyes with no back (the hair hung there over a neck the model never had)
    and, when `window`, the hair step's hole in its jaw's corner (40 to 80 degrees round from the front on one side,
    12 to 15 cm under the eyes); its scalp's foot lies at z -0.08: (points, faces, frame, patch)."""
    neck = trimesh.creation.cylinder(radius=0.05, height=0.1, sections=64)
    neck.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
    neck.apply_translation([0.0, -0.15, 0.0])
    neck = neck.subdivide().subdivide()
    points, faces = np.asarray(neck.vertices), np.asarray(neck.faces)
    middles = points[faces].mean(axis=1)
    round_from_front = np.degrees(np.arctan2(middles[:, 0], middles[:, 2]))
    gone = middles[:, 2] < 0.0
    if window:
        gone |= (round_from_front > 40) & (round_from_front < 80) & (middles[:, 1] < -0.12) & (middles[:, 1] > -0.15)
    frame = {"eyes_middle": np.zeros(3), "middle_x": 0.0, "centre": np.array([0.0, 0.0, -0.02])}
    heights = np.linspace(-0.03, 0.05, 9)
    foot = np.stack([np.zeros(9), heights, -0.08 - 0.2 * (heights + 0.03)], axis=1)
    patch = {"points": np.vstack([foot, [[0.0, 0.05, 0.09]]]), "hole": np.ones(10, dtype=bool),
             "directions": np.vstack([np.tile([0.0, 0.0, -1.0], (9, 1)), [[0.0, 0.0, 1.0]]]),
             "triangles": np.zeros((0, 3), np.int64)}
    return points, faces[~gone], frame, patch


def neck_closes_jaw():
    """The neck closed over the toy's jaw-corner hole: the share of rays out from the neck's middle through the hole
    that meet the tube within 3 mm inside the skin's 5 cm."""
    points, faces, frame, patch = neck_toy(True)
    tube, triangles = scalp.neck_closed(points, faces, np.zeros(len(faces), dtype=bool),
                                        np.ones(len(faces), dtype=bool), frame, patch)
    angle, height = np.meshgrid(np.radians(np.linspace(45, 75, 7)), np.linspace(-0.145, -0.125, 5))
    ways = np.stack([np.sin(angle.ravel()), np.zeros(angle.size), np.cos(angle.ravel())], axis=1)
    starts = np.stack([np.zeros(angle.size), height.ravel(), np.zeros(angle.size)], axis=1)
    met = scalp.met_along(tube, triangles, starts, ways)
    return round(float(np.mean(np.abs(met - 0.05) < 0.003)), 2)


def neck_under_jaw():
    """The neck closed all round under the jaw (`scalp.JAW_KEPT_M`) over the toy whose skin is whole in front: the share
    of rays out from its middle 20 to 70 degrees off the front, 12.5 to 14.5 cm under the eyes, that meet the tube
    within 3 mm inside the skin's 5 cm."""
    points, faces, frame, patch = neck_toy(False)
    tube, triangles = scalp.neck_closed(points, faces, np.zeros(len(faces), dtype=bool),
                                        np.ones(len(faces), dtype=bool), frame, patch)
    angle, height = np.meshgrid(np.radians(np.linspace(20, 70, 6)), np.linspace(-0.145, -0.125, 5))
    ways = np.stack([np.sin(angle.ravel()), np.zeros(angle.size), np.cos(angle.ravel())], axis=1)
    starts = np.stack([np.zeros(angle.size), height.ravel(), np.zeros(angle.size)], axis=1)
    met = scalp.met_along(tube, triangles, starts, ways)
    return round(float(np.mean(np.abs(met - 0.05) < 0.003)), 2)


def neck_meets_nape():
    """The neck's back closed under a bob over a neck the model never had: its deepest point behind (z, m), over the
    toy whose scalp's foot lies at z -0.08, 8 cm behind its middle."""
    points, faces, frame, patch = neck_toy(False)
    tube, _ = scalp.neck_closed(points, faces, np.zeros(len(faces), dtype=bool), np.ones(len(faces), dtype=bool),
                                frame, patch)
    return round(float(tube[:, 2].min()), 4)


def scalp_holds_jaw():
    """The scalp over a ball's back hair with a jaw's corner standing 18% out at the seam 8 cm under the eyes and an
    ear as far out 2 cm over them: (the scalp meets the jaw's skin within 1 mm, fewer than 10 of its directions
    held to the ear's)."""
    ball = trimesh.creation.icosphere(subdivisions=5, radius=0.09)
    points, faces = np.asarray(ball.vertices).copy(), np.asarray(ball.faces)
    for middle in ([0.05, -0.075, 0.004], [-0.09, 0.0, 0.0]):
        middle = np.asarray(middle) / np.linalg.norm(middle) * 0.09
        points *= (1.0 + 0.2 * np.exp(-(np.sum((points - middle) ** 2, axis=1) / 0.015 ** 2) ** 2))[:, None]
    middles = points[faces].mean(axis=1)
    hair = (middles[:, 2] < -0.002) & (middles[:, 1] > -0.085)
    frame = {"eyes_middle": np.array([0.0, -0.02, 0.09]), "middle_x": 0.0, "centre": np.zeros(3)}
    patch = scalp.scalp_patch(points, faces, hair, frame)
    skin = scalp.first_hit(points, faces[~hair], scalp.origin(frame), patch["directions"])
    out = ~patch["hole"] & (skin > 1.12 * 0.09)
    jaw, ear = out & (patch["directions"][:, 0] > 0.3), out & (patch["directions"][:, 0] < -0.5)
    return bool(jaw.sum() > 10 and np.abs(patch["distance"] - skin)[jaw].max() < 0.001), bool(ear.sum() < 10)


def shell_layers():
    """The layer read across a 2 cm thick spherical shell of hair round a head's middle: at its inner 2 mm and at its
    outer 2 mm (0 is the scalp's side, 1 the outer surface)."""
    low = np.full(3, -0.12)
    shape = (121, 121, 121)
    middles = low + np.argwhere(np.ones(shape, dtype=bool)) * volume.VOXEL_M
    distance = np.linalg.norm(middles, axis=1).reshape(shape)
    filled = (distance > 0.09) & (distance < 0.11)
    layer, _ = volume.layered(filled, low, np.zeros(3))
    return (float(layer[filled & (distance < 0.092)].mean()) < 0.2, float(layer[filled & (distance > 0.108)].mean())
            > 0.8)


def skin_laid():
    """The model's skin at the hole's edge after `scalp.laid`: its largest distance off the scalp (m), over the toy
    with its hair's foot standing 3 mm more as a lip round the hole (the toy's edge already stands up to 8 mm)."""
    points, faces, _, _, frame = toy()
    hair_faces = labelled()
    patch = scalp.scalp_patch(points, faces, hair_faces, frame)
    start = scalp.origin(frame)
    edge = np.unique(faces[hair_faces])
    lip = np.unique(faces[~hair_faces])
    lip = lip[np.isin(lip, edge)]
    lifted = points.copy()
    lifted[lip] += scalp_way(lifted[lip], start) * 0.003
    laid = scalp.laid(lifted, faces, hair_faces, patch, frame)
    return float(trimesh.Trimesh(patch["points"], patch["triangles"]).nearest.on_surface(laid[lip])[1].max())


def scalp_way(places, start):
    """Unit ways from `start` to the places."""
    away = places - start
    return away / np.linalg.norm(away, axis=1, keepdims=True)


def groove_and_streak():
    """The cosines of the read groove way and paint streak way with the true ones, on a corrugated plane (grooves
    along y, 3 mm apart) and on a flat plane painted with streaks running 30 degrees off its u axis."""
    xs, ys = np.meshgrid(np.linspace(0.0, 0.03, 61), np.linspace(0.0, 0.03, 61))
    flat = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    corner = (np.arange(60)[:, None] * 61 + np.arange(60)[None, :]).ravel()
    faces = np.vstack([np.column_stack([corner, corner + 1, corner + 62]),
                       np.column_stack([corner, corner + 62, corner + 61])])
    wavy = flat + np.column_stack([np.zeros((xs.size, 2)), 0.0005 * np.sin(2.0 * np.pi * xs.ravel() / 0.003)])
    middle = np.abs(flat[faces].mean(axis=1)[:, :2] - 0.015).max(axis=1) < 0.01
    groove, _ = flow.grooves(wavy, faces, middle)
    rows, columns = np.mgrid[:512, :512]
    along = np.radians(30.0)
    texture = (127 + 100 * np.sin(2.0 * np.pi * (-columns * np.sin(along) - rows * np.cos(along)) / 8.0))
    texture = np.repeat(texture[..., None], 3, axis=2).astype(np.uint8)
    uv = flat[:, :2] / 0.03
    streak, _ = flow.streaks(flat, faces, uv, texture, middle)
    truth = np.array([np.cos(along), np.sin(along), 0.0])
    return (round(float(np.median(np.abs(groove[:, 1]))), 2) > 0.95,
            round(float(np.median(np.abs(streak @ truth))), 2) > 0.95)


def photo_waves():
    """The curl read off pictures of strands 1.2 mm apart: straight ones and ones waving 5 mm every 4 cm."""
    metre = 0.0004
    rows, columns = np.mgrid[:curl.SIZE, :curl.SIZE] * metre
    found = []
    for amplitude in (0.0, 0.005):
        phase = (columns - amplitude * np.sin(2.0 * np.pi * rows / 0.04)) / 0.0012
        lab = np.stack([50.0 + 20.0 * np.sin(2.0 * np.pi * phase), np.zeros_like(phase), np.zeros_like(phase)], -1)
        angle, _, _ = curl.strand_ways(lab, metre)
        usable = np.zeros(angle.shape, dtype=bool)
        usable[50:-50, 50:-50] = True
        found.append(curl.curl_of(curl.lines_of(angle, usable, metre)))
    straight, waving = found
    return (straight["wave_m"] == 0.0 and straight["curly"] == 0.0,
            0.0035 < waving["wave_m"] < 0.0065 and 0.03 < waving["period_m"] < 0.05 and waving["curly"] > 0.5)


def roots_and_beard_fade():
    """The roots' density share at the paint's hairline, 2 and 4 mm over it; whether the chin in front grows
    scalp hair; the share of beard roots kept at the beard's edge under the chin and NECK_FADE_M in."""
    fade = strands.hairline_fade(np.array([0.0, 0.002, 0.004]))
    frame = {"centre": np.zeros(3), "eyes": np.array([[-0.03, 0.0, 0.08], [0.03, 0.0, 0.08]]),
             "eyes_middle": np.array([0.0, 0.0, 0.08]), "nose": np.array([0.0, -0.035, 0.1])}
    chin = strands.grows_here(np.array([[0.0, -0.1, 0.06]]), frame, False)[0]
    smooth = np.array([[0.0, -0.14, 0.05], [0.0, -0.14 + beard.NECK_FADE_M, 0.05], [1.0, 1.0, 1.0]])
    places = np.repeat(smooth[:2], 2000, axis=0)
    faces = np.array([[0, 0, 2], [0, 1, 1]])
    kept = beard.neck_kept(places, smooth, faces, np.array([False, True]), frame, np.random.default_rng(3))
    return (round(float(fade[0]), 2) == hair.BABY_DENSITY[1] and 0.6 < fade[1] < 0.8 and fade[2] == 1.0,
            chin == 0.0, kept[:2000].mean() < 0.05 and kept[2000:].mean() > 0.95)


def swatch_rows():
    """A strand swatch table as `fibre.swatch_table` writes one, from a made-up smooth law: a pure head's lightness
    falling with its melanin (lighter for more redness) and its a* rising with its redness and melanin, a grey head's
    the white strands' and the pigmented ones' mixed, its spread rising as they differ."""
    rows, whitest = [], 80.0 * (1.0 - fibre.SWATCH["melanin"][0]) ** 0.7 + 6.0
    for case in fibre.swatch_cases():
        pigmented = 80.0 * (1.0 - case["melanin"]) ** 0.7 + 6.0 + 4.0 * case["redness"]
        white = case["white_share"]
        lightness = white * whitest + (1.0 - white) * pigmented
        spread = 4.0 + 0.4 * white * (1.0 - white) * (whitest - pigmented)
        rows.append({**{key: case[key] for key in ("melanin", "redness", "white_share")},
                     "lab": [lightness, 1.0 + 6.0 * case["redness"] * case["melanin"] * (1.0 - white), 3.0],
                     "spread": spread})
    return rows


def fibre_fitted():
    """A darker head gets more melanin; a warm head darker than the darkest swatch its hue's redness (1 here); a grey
    head the white share, melanin and redness whose swatch shows its colour and spread (0.7, 0.6 and 0.5). Each photo
    colour is the swatch's plus `fibre.DRAWN_OFFSET` (the sheet's head draws darker than the swatch's ball)."""
    rows = swatch_rows()
    offset = fibre.DRAWN_OFFSET
    dark = fibre.fibre_of(np.array([0.1, 0.07, 0.05]), np.array([12.0, 2.0, 3.0]) + offset, 6.0, rows)
    light = fibre.fibre_of(np.array([0.5, 0.4, 0.3]), np.array([45.0, 4.0, 12.0]) + offset, 6.0, rows)
    warm = fibre.fibre_of(np.array([0.08, 0.06, 0.05]), np.array([12.0, 7.0, 3.0]) + offset, 6.0, rows)
    pigmented, whitest = 80.0 * 0.4 ** 0.7 + 6.0 + 2.0, 80.0 * (1.0 - fibre.SWATCH["melanin"][0]) ** 0.7 + 6.0
    grey = fibre.fibre_of(np.array([0.65, 0.65, 0.64]),
                          np.array([0.7 * whitest + 0.3 * pigmented, 1.0 + 6.0 * 0.5 * 0.6 * 0.3, 3.0]) + offset,
                          4.0 + 0.4 * 0.7 * 0.3 * (whitest - pigmented), rows)
    return (dark["melanin"] > light["melanin"] and light["white_share"] == 0.0
            and warm["redness"] > 0.95 and warm["melanin"] > 0.95
            and abs(grey["white_share"] - 0.7) < 0.03 and abs(grey["melanin"] - 0.6) < 0.03
            and abs(grey["redness"] - 0.5) < 0.06,
            f"dark {dark['melanin']}, light {light['melanin']}, warm m {warm['melanin']} r {warm['redness']}, grey "
            f"white {grey['white_share']} m {grey['melanin']} r {grey['redness']}")


def silver_photo():
    """A 512-pixel close-up on a plain light grey backdrop (L 81): a silver bob as light as the backdrop (L 78, its
    strands' lightness spread 5), a skin face with two dark pupils under it: (sRGB picture, the hair's truth)."""
    size = 512
    rows, columns = np.mgrid[:size, :size]
    lab = np.zeros((size, size, 3))
    lab[...] = (81.0, 0.8, 1.9)
    head = ((columns - 256) / 150.0) ** 2 + ((rows - 230) / 190.0) ** 2 < 1.0
    hair = head & (rows < 330)
    strands = np.random.default_rng(5).normal(0.0, 5.0, size)[columns]
    lab[hair] = np.stack([78.0 + strands, np.full(size, 3.0)[columns], np.full(size, 4.0)[columns]], -1)[hair]
    face = ((columns - 256) / 95.0) ** 2 + ((rows - 250) / 130.0) ** 2 < 1.0
    face &= rows > 120
    lab[face] = (70.0, 15.0, 22.0)
    for column in (215, 297):
        lab[np.hypot(columns - column, rows - 200) < 5] = (10.0, 0.0, 0.0)
    from skimage.color import lab2rgb
    return np.clip(lab2rgb(lab), 0.0, 1.0), hair & ~face & (rows < 200 + labels.CLOSEUP["chin"] * 82)


def silver_hair_read():
    """The share of a silver bob's pixels the photo's hair holds, and the share of what it holds that is not hair."""
    picture, truth = silver_photo()
    found = labels.photo_hair(picture)
    return round(float((found & truth).sum() / truth.sum()), 2), round(float((found & ~truth).sum() / found.sum()), 2)


def white_bits_kept_as_hair():
    """The share of a white island on the toy's forehead labelled hair, the toy's hair silver and its coat a scarf's
    cream (the island nearer the cream, as an older woman's fringe bits were), and of brows painted in the dark toy
    hair's own colour there."""
    points, faces, colours, truth, frame = toy()
    middles = points[faces].mean(axis=1)
    over = middles[:, 1] - frame["eyes_middle"][1]
    forehead = (over > labels.FACE_BOX["over_eyes_m"]) & (over < 0.03) & (middles[:, 2] > 0.0) & ~truth
    forehead &= cKDTree(middles[truth]).query(middles, workers=-1)[0] < labels.STRAY_M / 2.0
    silver = colours.copy()
    silver[truth] = (82.0, 1.0, 2.0)
    silver[len(trimesh.creation.icosphere(subdivisions=4).faces):] = (90.0, 3.0, 9.0)
    silver[forehead] = (89.0, 3.0, 8.0)
    browed = colours.copy()
    browed[forehead] = COLOURS["hair"]
    found = [labels.hair_labels(points, faces, painted, frame, False, 0.3)[0][forehead] for painted in (silver, browed)]
    return int(forehead.sum() > 5), round(float(found[0].mean()), 2), round(float(found[1].mean()), 2)


def forehead_roots():
    """Whether hair roots 3 cm over the eyes in front of the forehead, beside it 40 degrees round, and 6 cm over
    them in front: under a fringe, then with none (the paint's hairline holds)."""
    frame = {"centre": np.zeros(3), "eyes": np.array([[-0.03, 0.0, 0.08], [0.03, 0.0, 0.08]]),
             "eyes_middle": np.array([0.0, 0.0, 0.08])}
    turned = np.radians(40.0)
    places = np.array([[0.0, 0.03, 0.09], [0.09 * np.sin(turned), 0.03, 0.09 * np.cos(turned)], [0.0, 0.06, 0.08]])
    return tuple(tuple(strands.grows_here(places, frame, fringed).tolist()) for fringed in (True, False))


def toy_head(count=4000, seed=0):
    """Points on a squashed sphere (radius about 0.1 m) with three bumps: a nose on its front (-y), an ear and a bun,
    so no turn maps it onto itself."""
    rng = np.random.default_rng(seed)
    way = rng.normal(size=(count, 3))
    way /= np.linalg.norm(way, axis=1, keepdims=True)
    points = way * np.array([0.08, 0.1, 0.12])
    for centre, rise in (([0, -1, 0], 0.03), ([1, 0, 0.3], 0.02), ([-0.5, 0.5, 0.7], 0.025)):
        centre = np.array(centre, float) / np.linalg.norm(centre)
        points += (rise * np.exp(-((way - centre) ** 2).sum(1) / 0.08))[:, None] * way
    return points


def turned(degrees, axis):
    """The rotation of `degrees` about the unit `axis`."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    angle = np.radians(degrees)
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * cross + (1 - np.cos(angle)) * cross @ cross


TRUTH = (0.3, turned(20, [0.2, 0.1, 1.0]), np.array([0.05, -0.2, 1.5]))


def nearest_among(points):
    """A nearest-index answer over `points` (a KD tree)."""
    tree = cKDTree(points)

    def answer(queries):
        return tree.query(queries)[1]
    return answer


def similarity_found():
    """The exact fit's largest point error (m), and its turn's determinant fitted onto the toy's mirror image (a
    turn, +1, never a reflection)."""
    source = toy_head()
    found = head_swap.similarity(source, head_swap.moved(source, *TRUTH))
    mirrored = head_swap.similarity(source, source * np.array([-1.0, 1.0, 1.0]))
    return (float(np.abs(head_swap.moved(source, *found) - head_swap.moved(source, *TRUTH)).max()),
            round(float(np.linalg.det(mirrored[1])), 6))


def icp_found():
    """The trimmed ICP's largest point error (m) on the clean points, from a start off in scale and turn, a fifth of
    its source points stray."""
    source = toy_head(1500, seed=1)
    target = head_swap.moved(toy_head(6000, seed=2), *TRUTH)
    strays = np.random.default_rng(3).uniform(-0.15, 0.15, size=(300, 3))
    start = (TRUTH[0] * 1.15, TRUTH[1], TRUTH[2] + np.array([0.004, -0.003, 0.005]))
    found = head_swap.trimmed_icp(np.vstack([source, strays]), target, start, nearest_among)
    clean = toy_head(500, seed=4)
    return float(np.abs(head_swap.moved(clean, *found[:3]) - head_swap.moved(clean, *TRUTH)).max())


def scale_scanned():
    """The scale `lowest` reads from misses scanned on a parabola whose least lies at 0.257."""
    scales = np.arange(0.16, 0.38, 0.02)
    return round(head_swap.lowest(scales, (scales - 0.257) ** 2 + 0.003), 6)


def seam_weights():
    """The seam's weight at the cut, halfway and at the band's top."""
    return [round(float(weight), 6) for weight in head_swap.eased([0.0, 0.5, 1.0], 1.0)]


def texel_share():
    """The texels of the lower-left half of a 64-texel square texture, over all its texels."""
    columns, _, weights = head_swap.texels_of([[0, 0], [1, 0], [0, 1]], 64)
    return len(columns) / 64 ** 2, bool((weights.sum(1) > 0.999).all())


def frames_agree():
    """The largest gap between a glTF point moved by the glTF matrix and the same point moved in Blender's frame."""
    matrix = np.eye(4)
    matrix[:3, :3] = TRUTH[0] * TRUTH[1]
    matrix[:3, 3] = TRUTH[2]
    point_gltf = np.array([0.1, 0.2, 0.3, 1.0])
    point_blender = np.array([point_gltf[0], -point_gltf[2], point_gltf[1], 1.0])
    moved_blender = matrix @ point_blender
    moved_gltf = head_swap.gltf_matrix(matrix) @ point_gltf
    return float(np.abs(moved_gltf - np.array([moved_blender[0], moved_blender[2], -moved_blender[1], 1.0])).max())
def skin_flat_grid(colour, size_m=0.1):
    """A flat front grid for the skin's step: `colour(x, y)` painted, every pixel seen and facing forward."""
    xs = (np.arange(int(size_m / skin.STEP_M)) + 0.5) * skin.STEP_M - size_m / 2
    grid_x, grid_y = np.meshgrid(xs, xs)
    ones = np.ones_like(grid_x)
    return {"xs": xs, "ys": xs, "depth": ones * 0.1, "seen": ones > 0, "facing": ones, "normal_x": 0 * ones,
            "normal_y": 0 * ones, "colour": colour(grid_x, grid_y)}


def skin_blobs(x, y):
    """A seeded paint of soft blobs a few millimetres across (the face's detail), sRGB."""
    rng = np.random.default_rng(3)
    total = np.zeros(np.shape(x))
    for centre_x, centre_y, radius in zip(rng.uniform(-0.05, 0.05, 160), rng.uniform(-0.05, 0.05, 160),
                                          rng.uniform(0.002, 0.005, 160)):
        total += np.exp(-0.5 * ((x - centre_x) ** 2 + (y - centre_y) ** 2) / radius ** 2)
    return np.stack([0.75 - 0.2 * np.tanh(total), 0.55 - 0.15 * np.tanh(total), 0.45 - 0.1 * np.tanh(total)], -1)


def skin_registered():
    """The photo found from a start 4 px and 2% off: its true place under half a pixel off over the face."""
    truth = skin.similarity(np.array([[-0.03, 0.0], [0.03, 0.0]]), np.array([[136.0, 210.0], [376.0, 200.0]]))
    rows, cols = np.mgrid[:420, :512]
    inverse = np.linalg.inv(np.vstack([truth, [0, 0, 1]]))
    model_x = inverse[0, 0] * cols + inverse[0, 1] * rows + inverse[0, 2]
    model_y = inverse[1, 0] * cols + inverse[1, 1] * rows + inverse[1, 2]
    photo = skin_blobs(model_x, model_y)
    grid = skin_flat_grid(skin_blobs, 0.08)
    start = truth * np.array([[1.02], [1.02]]) + np.array([[0, 0, 4.0], [0, 0, -3.0]])
    warp, _ = skin.registered(grid, photo, start)
    inner = slice(40, -40)
    found = np.stack(skin.mapped(warp, grid["xs"][inner], grid["ys"][inner]), -1)
    true = np.stack(skin.mapped({**warp, "matrix": truth, "displacement": 0 * warp["displacement"]},
                                grid["xs"][inner], grid["ys"][inner]), -1)
    return bool(np.abs(found - true).max() < 1.0), round(float(np.abs(found - true).max()), 3)


def skin_light_off():
    """The photo's light taken off: a shading that follows the normal flattened, a nose's gloss taken out, plain
    skin kept."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    tilt = np.sin(grid["xs"] * 20.0)[None, :] * np.ones((len(grid["ys"]), 1))
    grid["normal_x"], grid["facing"] = tilt, np.sqrt(1 - tilt ** 2)
    albedo = np.array([0.5, 0.3, 0.22])
    lit = albedo * (0.9 + 0.1 * tilt)[..., None]
    light, _ = skin.shading(grid, lit, np.ones(tilt.shape))
    flat = eyes.luminance(lit / light)
    glossy = albedo + 0.12
    cleaned, excess = skin.gloss_free(np.array([glossy, albedo]), np.full(2, eyes.luminance(albedo)),
                                      np.tile(albedo / albedo[0], (2, 1)))
    left = eyes.luminance(cleaned[0]) / eyes.luminance(albedo) - 1.0
    return [bool(flat.std() / flat.mean() < 0.02),
            bool(left < excess[0] / 2.0 and np.allclose(cleaned[0] / cleaned[0, 0], albedo / albedo[0], atol=0.01)),
            bool(np.abs(cleaned[1] - albedo).max() < 0.005)]


def skin_hollow_light_off():
    """A hollow the model's own front shuts reads shut, and the photo's darker, warmer light in it is divided out to
    the skin's colour round it (the render makes the hollow's shade again)."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    rows, cols = np.indices(grid["depth"].shape)
    pit = np.hypot(rows - 100, cols - 100) < 30
    grid["depth"] = np.where(pit, 0.1 - 0.015, 0.1)
    shut = skin.occlusion(grid)
    albedo = np.array([0.5, 0.3, 0.22])
    lit = albedo * (1.0 - shut[..., None] * np.array([0.6, 0.8, 0.9]))
    light, _ = skin.shading(grid, lit, np.ones(shut.shape))
    flat = lit / light
    inner = np.hypot(rows - 100, cols - 100) < 10
    return [bool(shut[inner].mean() > shut[~pit].mean() + 0.3),
            bool(np.abs(flat[inner].mean(axis=0) / flat[~pit].mean(axis=0) - 1.0).max() < 0.08)]


def skin_matte_beside_brows():
    """Plain skin between a dark brow and a dark lid opening is no highlight (`skin.matte_skin` reads its matte over
    plain skin, `skin.plain_skin`): pressed by under 1%, while a real highlight on the cheek is still pressed."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    rows, cols = np.indices(grid["seen"].shape)
    albedo = np.array([0.5, 0.3, 0.22])
    flat = np.ones(rows.shape + (3,)) * albedo
    flat[(rows > 60) & (rows < 72)] *= 0.12  # a brow
    flat[(rows > 80) & (rows < 88)] *= 0.05  # the lashes and the lid opening
    flat[(np.abs(rows - 150) < 3) & (np.abs(cols - 100) < 3)] *= 1.4  # a highlight on the cheek
    matte, chroma = skin.matte_skin(flat, np.ones(rows.shape))
    cleaned, _ = skin.gloss_free(flat, matte, chroma)
    between = (rows > 73) & (rows < 79)
    left = eyes.luminance(cleaned[between]) / eyes.luminance(albedo)
    spot = eyes.luminance(cleaned[150, 100]) / eyes.luminance(albedo)
    return [bool(np.abs(left - 1.0).max() < 0.01), bool(spot < 1.25)]


def skin_socket_shade_off():
    """A socket the model's own front shuts, the photo's shade in it deeper than one line fitted over the whole face
    takes off (`skin.hollows`): within 10% of the open skin after (18% under before), and a stain on open skin keeps
    its own dark."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    rows, cols = np.indices(grid["depth"].shape)
    pit = np.hypot(rows - 60, cols - 100) < 22
    grid["depth"] = np.where(pit, 0.1 - 0.015, 0.1)
    shut = skin.occlusion(grid)
    albedo = np.array([0.5, 0.3, 0.22])
    stain = np.hypot(rows - 150, cols - 100) < 10
    lit = albedo * (1.0 - shut[..., None] * [0.6, 0.8, 0.9])
    lit[stain] *= 0.6
    skin_weight = np.ones(rows.shape)
    light, _ = skin.shading(grid, lit, skin_weight)
    light = light * skin.hollows(grid, lit / light, skin_weight)[..., None]
    flat = eyes.luminance(lit / light)
    level = flat[~(pit | stain) & (np.hypot(rows - 100, cols - 100) < 90)].mean()
    return [bool(abs(flat[np.hypot(rows - 60, cols - 100) < 8].mean() / level - 1.0) < 0.1),
            bool(flat[np.hypot(rows - 150, cols - 100) < 5].mean() / level < 0.7)]


def skin_photo_kept_off():
    """The photo's face leaves out its fringe (strands with skin between, from the top edge) and its lid openings but
    keeps its brows and a moustache under the pupils; the model's painted fringe wears no photo, its beard's middle
    may; the share rises over EDGE_FEATHER_M from its outer edge."""
    rows, cols = np.indices((200, 200))
    photo = np.ones((200, 200, 3)) * [0.85, 0.65, 0.55]
    strands = (rows < 70) & ((rows < 40) | (cols % 10 < 6))
    photo[strands] = 0.7
    photo[(np.abs(rows - 80) < 3) & (np.abs(cols - 60) < 20)] = [0.2, 0.15, 0.1]
    photo[(np.abs(rows - 150) < 5) & (np.abs(cols - 100) < 30)] = [0.2, 0.15, 0.1]  # a moustache, by a hair's
    photo[(rows > 150) & (np.abs(cols - 100) < 4)] = [0.2, 0.15, 0.1]  # line to the picture's edge
    pupils = np.array([[60.0, 100.0], [140.0, 100.0]])
    face = skin.face_mask(photo, 2000.0, pupils)
    marks = {"eyes": [{"upper": [[50, 100], [60, 95], [70, 100]], "lower": [[50, 100], [60, 105], [70, 100]]}]}
    opening = skin.eye_openings(face.shape, marks, 2000.0)
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * [0.85, 0.65, 0.55])
    grid["colour"][(grid["ys"] > 0.03)[:, None] & np.ones((1, len(grid["xs"])), bool)] = 0.7
    grid["colour"][(grid["ys"] < -0.03)[:, None] & (np.abs(grid["xs"]) < 0.02)[None, :]] = [0.2, 0.15, 0.1]
    free = skin.model_hair_free(grid, np.array([[-0.03, 0.0], [0.03, 0.0]]))
    flat = np.zeros(grid["depth"].shape)
    flat[20:180, 20:180] = 1.0
    share = skin.grid_share(grid, flat, np.full(flat.shape, np.inf))
    return [bool(face[55, 103] < 0.2), bool(face[80, 60] > 0.8), bool(face[150, 100] > 0.8),
            bool(opening[100, 60] and not opening[120, 60]),
            bool(free[190, 100] == 0 and free[100, 100] == 1 and free[20, 100] == 1),
            bool(share[100, 22] < 0.3 and share[100, 40] > 0.95)]


def skin_photo_beard_worn():
    """A bearded man's photo beard (his hairs against the skin between them) joins his face, the hood's grey folds
    under it and the backdrop beside it never; a shaded cheek as dark is no beard; his model's beard painted on
    the cheeks is head hair to a shaven man's step, never to his."""
    rows, cols = np.indices((200, 200))
    photo = np.ones((200, 200, 3)) * 0.85
    photo[(np.abs(cols - 100) < 60) & (rows > 30) & (rows < 135)] = [0.85, 0.65, 0.55]
    beard = (np.abs(cols - 100) < 60) & (rows >= 135) & (rows < 175)
    photo[beard] = [0.25, 0.17, 0.12]
    photo[beard & (rows % 4 == 0) & (cols % 4 == 0)] = [0.85, 0.65, 0.55]  # the skin between the hairs
    photo[beard & (cols >= 135)] = [0.45, 0.32, 0.26]  # a cheek in shade, its pores faint
    photo[beard & (cols >= 135) & ((rows + cols) % 2 == 0)] = [0.47, 0.34, 0.28]
    photo[(np.abs(cols - 100) < 80) & (rows >= 175)] = np.where((cols[rows >= 175] % 3 == 0)[:, None], 0.3, 0.45)[
        np.abs(cols[rows >= 175] - 100) < 80]  # the hood's folds
    pupils = np.array([[70.0, 100.0], [130.0, 100.0]])
    found = skin.photo_beard(photo, 1000.0, pupils)
    share = skin.hair_share(photo, 1000.0, pupils)
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * [0.85, 0.65, 0.55])
    grid["colour"][(grid["ys"] < -0.035)[:, None] & (np.abs(grid["xs"]) > 0.042)[None, :]] = [0.2, 0.15, 0.1]
    model_pupils = np.array([[-0.03, 0.0], [0.03, 0.0]])
    shaven, bearded = (skin.model_hair_free(grid, model_pupils, beard) for beard in (False, True))
    return [bool(found[150, 100] and found[152, 104]), bool(not found[185, 100]), bool(not found[150, 20]),
            bool(share[155, 100] > 0.9 and share[155, 150] < 0.1),
            bool(shaven[10, 192] == 0 and bearded[10, 192] == 1)]


def skin_shares():
    """A point wears the photo only facing forward, on the front, inside the photo's face and clear of the eye."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    grid["facing"][:, :40] = 0.05  # the left side turned away
    mask = np.ones(grid["depth"].shape)
    mask[:40, :] = 0.0  # the bottom outside the photo's face
    turn = np.linspace(0, 2 * np.pi, 200)
    floor = np.column_stack([0.02 + np.outer(np.linspace(0, 0.005, 10), np.cos(turn)).ravel(),
                             np.outer(np.linspace(0, 0.005, 10), np.sin(turn)).ravel(), np.full(2000, 0.1)])
    coarse = {"share": skin.grid_share(grid, mask, skin.eye_floor_distance(grid, floor))}
    points = np.array([[0.0, 0.02, 0.1], [-0.04, 0.02, 0.1], [0.0, -0.04, 0.1], [0.02, 0.0, 0.1], [0.0, 0.02, 0.05]])
    shares = skin.point_shares(grid, coarse, points)
    zone = skin.tzone(np.array([[0.0, 0.0, 0.1], [0.045, 0.01, 0.1]]), np.zeros(3))
    return [bool(shares[0] > 0.95), *(bool(value < 0.05) for value in shares[1:]), bool(zone[0] > 0.9),
            bool(zone[1] < 0.1)]
def iris_unrolled():
    """A photo's iris (radius 30 px, its pupil 9 px, a catchlight on its pupil's edge, MediaPipe's circle 15% wide):
    its pupil read at its share, the catchlight gone from the iris picture, the white outside it."""
    picture = np.ones((300, 400, 3)) * (0.85, 0.82, 0.8)
    rows, cols = np.mgrid[:300, :400]
    marks = lid_marks(60.0, 40.0)
    for eye in marks["eyes"]:
        col, row = eye["iris_centre"][0], 150.0
        eye["iris_centre"], eye["iris_radius"] = [col + 2.0, row - 1.0], 30.0 / eyes.IRIS_PICTURE["radius"]
        eye["upper"] = (np.asarray(eye["upper"]) + [0.0, 50.0]).tolist()
        eye["lower"] = (np.asarray(eye["lower"]) + [0.0, 50.0]).tolist()
        out = np.hypot(cols - col, rows - row)
        picture[out < 30.0] = (0.3, 0.18, 0.1) * (1.0 + 0.15 * np.sin(np.arctan2(rows - row, cols - col) * 12))[
            out < 30.0, None]
        picture[out < 9.0] = 0.02
        picture[np.hypot(cols - col - 13, rows - row + 12) < 4.0] = 1.0
    sclera = (0.68, 0.58, 0.5)
    texture, stats = eyes.iris_picture(picture, marks, sclera, 0.125)
    size = len(texture)
    across = (np.arange(size) + 0.5) / size - 0.5
    out = np.hypot(*np.meshgrid(across, across)) / 0.125
    ring = (out > 0.4) & (out < 0.8)
    light = eyes.luminance(texture)
    return [bool(abs(stats["pupil_share"] - 0.3) < 0.025), bool(light[ring].max() < 1.5 * np.median(light[ring])),
            bool(np.allclose(texture[out > 1.1], sclera))]


def lashes_by_photo():
    """A photo with dense dark lashes over its upper lids gets the full lashes; one with a few gets fewer, never under
    the least."""
    shares = []
    for every in (2, 9):
        picture = np.ones((200, 400, 3)) * 0.75
        marks = lid_marks(30.0, 12.0)
        for eye in marks["eyes"]:
            for col, row in np.asarray(eye["upper"])[2:-2]:
                for step in range(-12, 13, every):
                    picture[int(row) - 14:int(row) - 1, int(col) + step] = 0.1
        shares.append(lids.lash_share(picture, marks))
    return [shares[0] == 1.0, lids.LASH_PHOTO["least"] <= shares[1] < 0.8]


def paint_lifted():
    """The paint's dark baked band (a socket's shade) lifted to the skin round it, plain skin left, a dark-haired
    piece (not skin's colour) left alone."""
    def paint(x, y):
        colour = np.ones(x.shape + (3,)) * np.array([0.8, 0.62, 0.52])
        colour[np.abs(y) < 0.003] *= 0.75
        colour[x > 0.03] = (0.1, 0.08, 0.07)
        return colour
    grid = skin_flat_grid(paint, 0.1)
    gain, dark = skin.paint_shade(grid)
    middle = len(grid["ys"]) // 2
    lifted = skin.linear(grid["colour"][middle, 50]) * gain[middle, 50]
    plain = skin.linear(grid["colour"][middle + 40, 50])
    return [bool(np.abs(lifted / plain - 1.0).max() < 0.15), bool(np.allclose(gain[middle + 40, 50], 1.0)),
            bool(dark[middle, 190] == 0.0)]


def steep_point_seen():
    """A point on a steep side (facing 0.3, its depth read 2 mm off by the front's pixels) is on the front; one 5 mm
    behind it is not."""
    grid = skin_flat_grid(lambda x, y: np.ones(x.shape + (3,)) * 0.5)
    grid["facing"][:] = 0.3
    points = np.array([[0.0, 0.0, 0.102], [0.0, 0.0, 0.095]])
    return skin.visible(grid, points).tolist()


def paint_toned():
    """The model's warm, dark skin paint (its broad tone a shade band and a rust patch) given the photo skin's colour
    statistics: its mean within a Lab unit of the photo's, its broad spread no wider than the photo's, its hair (not
    skin) untouched."""
    rows, cols = np.mgrid[:200, :200]
    texture = np.ones((200, 200, 3)) * np.array([0.55, 0.33, 0.22])
    texture[60:80] *= 0.6  # a baked shade band
    texture[120:160, 20:80] = (0.62, 0.3, 0.12)  # a rust patch
    texture[:, 180:] = (0.1, 0.08, 0.07)  # hair
    mask = cols < 170
    photo = np.ones((150, 150, 3)) * np.array([0.82, 0.62, 0.54])
    photo *= (1.0 + 0.03 * np.sin(np.arange(150) / 7.0))[:, None, None]
    photo_lab = skin.rgb2lab(photo)
    held = np.ones((150, 150), bool)
    toned, _ = skin.paint_toned(texture, mask, 2000.0, photo_lab, held)
    lab = skin.rgb2lab(toned)
    inner = (cols < 160) & (cols > 10)
    broad = skin.smoothed_over(lab, inner.astype(float), skin.PAINT_TONE["broad_m"] * 2000.0)
    photo_broad = skin.smoothed_over(photo_lab, held.astype(float), skin.PAINT_TONE["broad_m"] / skin.STEP_M)
    return [bool(np.abs(lab[inner].mean(axis=0) - photo_lab.mean(axis=(0, 1))).max() < 1.5),
            bool((broad[inner].std(axis=0) <= photo_broad.std(axis=(0, 1)) + 0.5).all()),
            bool(np.array_equal(toned[:, 180:], texture[:, 180:]))]


def layers_kept():
    """A hidden layer 3 mm behind the face, both pulled 5 mm forward onto one depth by the lid's move: the hidden layer
    stays at least LAYERS' `hidden_m` behind the face, the face moves as it was moved, a layer not free is left."""
    grid_x, grid_y = np.meshgrid(np.linspace(-0.005, 0.005, 21), np.linspace(-0.005, 0.005, 21))
    face = np.column_stack([grid_x.ravel(), grid_y.ravel(), np.zeros(grid_x.size)])
    hidden = face - [0.0, 0.0, 0.003]
    was = np.vstack([face, hidden])
    moved = was.copy()
    moved[:, 2] = 0.005
    free = np.ones(len(was), bool)
    kept = lids.layers_kept(was, moved, free)
    free[len(face):] = False
    left = lids.layers_kept(was, moved, free)
    count = len(face)
    return [bool((kept[:count] - kept[count:]).min() >= lids.LAYERS["hidden_m"] - 1e-9),
            bool(np.allclose(kept[:count], 0.005)), bool(np.allclose(left[count:], 0.005))]


def skin_wears_photo():
    """A dark painted patch (a painted brow) on skin is skin where it wears the photo and stays the model's own where
    it does not (all but its edge, which its neighbours settle)."""
    points, triangles = grid_mesh(np.linspace(0, 0.12, 61), np.linspace(0, 0.04, 21), lambda x, y: 0.0 * x)
    middles = points[triangles].mean(axis=1)
    brow = (np.abs(middles[:, 1] - 0.02) < 0.008) & ((np.abs(middles[:, 0] - 0.03) < 0.02)
                                                     | (np.abs(middles[:, 0] - 0.09) < 0.02))
    likeness = (~brow).astype(np.float64)
    shares = (points[:, 0] < 0.06).astype(np.float64)
    found = skin.skin_triangles(points, triangles, likeness, shares)
    left = brow & (middles[:, 0] < 0.06)
    right = brow & (middles[:, 0] > 0.06)
    return [bool(found[left].all()), bool(found[right].mean() < 0.2)]


LID_EYES = np.array([[-0.032, 0.0, 0.0], [0.032, 0.0, 0.0]])
LID_BALL = 0.012


def grid_mesh(xs, ys, depth):
    """A height-field mesh over the grid lines `xs`, `ys` with depth `depth(x, y)`: (points, triangles)."""
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel(), depth(grid_x, grid_y).ravel()])
    width = len(xs)
    corner = (np.arange(len(ys) - 1)[:, None] * width + np.arange(width - 1)[None, :]).ravel()
    return points, np.vstack([np.column_stack([corner, corner + 1, corner + width + 1]),
                              np.column_stack([corner, corner + width + 1, corner + width])])


def split_closed():
    """Whether half a grid's triangles split in four keep its area, leave no crack (a side inside the square used by
    one triangle only) and carry the UVs along (each new point's UV its place)."""
    points, triangles = grid_mesh(np.linspace(0, 1, 7), np.linspace(0, 1, 7), lambda x, y: 0.0 * x)
    chosen = points[triangles].mean(axis=1)[:, 0] < 0.5
    fine, carried, made = lids.refined(points, points[:, :2], triangles, chosen)
    corners = fine[made]
    area = 0.5 * np.abs(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])[:, 2]).sum()
    sides = np.sort(np.vstack([made[:, [0, 1]], made[:, [1, 2]], made[:, [2, 0]]]), axis=1)
    found, counts = np.unique(sides, axis=0, return_counts=True)
    middle = fine[found].mean(axis=1)
    inside = (middle[:, :2] > 1e-9).all(axis=1) & (middle[:, :2] < 1 - 1e-9).all(axis=1)
    return [bool(abs(area - 1.0) < 1e-9), bool((counts[inside] == 2).all()), bool(np.allclose(carried, fine[:, :2]))]


def lid_marks(half_width, half_height):
    """A photo's marks: two irises (10 px across) 200 px apart, each eye's lids an ellipse round its iris."""
    eyes_marks = []
    for col in (100.0, 300.0):
        turn = np.linspace(0.0, np.pi, 9)
        inner = 1.0 if col < 200 else -1.0  # the inner corner is towards the picture's middle
        upper = np.column_stack([col + inner * half_width * np.cos(turn), 100.0 - half_height * np.sin(turn)])
        lower = np.column_stack([col + inner * half_width * np.cos(turn), 100.0 + half_height * np.sin(turn)])
        eyes_marks.append({"upper": upper.tolist(), "lower": lower.tolist(), "iris_centre": [col, 100.0],
                           "iris_radius": 10.0})
    brows = [{"upper": [[60.0 + 80 * (col > 200) + 80 * k, 40.0] for k in (1, 0)],
              "lower": [[60.0 + 80 * (col > 200) + 80 * k, 60.0] for k in (1, 0)]} for col in (100.0, 300.0)]
    return {"eyes": eyes_marks, "brows": brows}


def photo_opening():
    """The photo's opening read round each eye (mm at 90 degrees, its half height laid by the frame's scale) and held
    inside the ball's silhouette at its corners."""
    laid = lids.photo_frame(lid_marks(30.0, 12.0), LID_EYES, 0.006)
    edges = lids.photo_outline(lid_marks(30.0, 12.0), laid, LID_EYES, LID_BALL)
    tall = [lids.edge_at(edge, 90.0) / (12.0 * laid.scale) for edge in edges]
    wide = [lids.edge_at(edge, 0.0) <= lids.CORNER_SHARE * LID_BALL + 1e-9 for edge in edges]
    return [bool(abs(value - 1.0) < 0.03) for value in tall] + [bool(value) for value in wide]


@functools.lru_cache(maxsize=1)
def lid_scene():
    """Two eyes (spheres) behind a face standing 4 mm in front of them, each opening an ellipse 13 mm tall with a deep
    floor inside; the photo's openings 9 mm tall: (points, triangles, eye views, old outlines, new edges)."""
    def depth(x, y):
        shares = [np.hypot((x - centre[0]) / 0.0115, y / 0.0065) for centre in LID_EYES]
        return np.where(np.min(shares, axis=0) < 1.0, -0.004, LID_BALL + 0.004)

    points, triangles = grid_mesh(np.arange(-0.06, 0.0601, 0.0007), np.arange(-0.027, 0.0271, 0.0007), depth)
    ball = trimesh.creation.icosphere(subdivisions=4, radius=LID_BALL)
    views = []
    for centre in LID_EYES:
        view = lids.front_view(np.asarray(ball.vertices) + centre, np.asarray(ball.faces), lids.eye_box(centre),
                               -np.inf)
        view["ball"] = view
        views.append(view)
    heads = [lids.front_view(points, triangles, lids.eye_box(centre), -1.0) for centre in LID_EYES]
    was = [lids.model_outline(head, view, centre) for head, view, centre in zip(heads, views, LID_EYES)]
    wanted = [1.0 / np.sqrt(np.cos(np.radians(lids.DEGREES)) ** 2 / 0.011 ** 2
                            + np.sin(np.radians(lids.DEGREES)) ** 2 / 0.0045 ** 2)] * 2
    return points, triangles, views, was, wanted


def lids_reshaped():
    """After the reshape: the opening's top and bottom on the photo's (within 0.4 mm), the lid's front just over the
    top and bottom margins LID_M over the eye (within 0.3 mm), and no lid point outside the opening inside the eye."""
    points, triangles, views, was, wanted = lid_scene()
    moved = lids.reshaped(points, np.zeros(len(points), bool), LID_EYES, LID_BALL,
                          [(old[0], old[1], new) for old, new in zip(was, wanted)], views)
    edge_ok, thin_ok, outside_ok = [], [], []
    for centre, view, new in zip(LID_EYES, views, wanted):
        head = lids.front_view(moved, triangles, lids.eye_box(centre), -1.0)
        found, _ = lids.model_outline(head, view, centre)
        edge_ok.append(all(abs(lids.edge_at(found, angle) - lids.edge_at(new, angle)) < 0.0004 for angle in (90, 270)))
        for angle in (90.0, 270.0):
            out = lids.edge_at(new, angle) + 0.001
            x, y = centre[0], out * np.sin(np.radians(angle))
            over = eyes.depth_at(head, [x], [y])[0] - eyes.depth_at(view, [x], [y])[0]
            thin_ok.append(abs(over - lids.LID_M) < 0.0003)
        degrees, reach = lids.polar(moved, centre)
        outside = (reach > lids.edge_at(new, degrees) + 0.0003) & (np.abs(moved[:, 0] - centre[0]) < 0.03)
        surface = eyes.depth_at(view, moved[outside, 0], moved[outside, 1])
        held = np.isfinite(surface)
        outside_ok.append(bool((moved[outside][held, 2] >= surface[held] + lids.GAP_M - 1e-6).all()))
    return [all(edge_ok), all(thin_ok), all(outside_ok)]


def lashes_grown():
    """Upper lashes root just outside the margin and rise to their tips, lower ones fall, all leaving forward."""
    points, triangles = grid_mesh(np.linspace(-0.03, 0.03, 31), np.linspace(-0.03, 0.03, 31),
                                  lambda x, y: 0.0 * x + 0.014)
    centre = np.zeros(3)
    head = lids.front_view(points, triangles, lids.eye_box(centre), -1.0)
    edge = np.full(len(lids.DEGREES), 0.008)
    found = []
    for upper in (True, False):
        made, _ = lids.lid_lashes(head, centre, edge, lids.lid_span(0.0, 180.0, upper), upper, 40,
                                  np.random.default_rng(1))
        out = np.hypot(made[:, 0, 0], made[:, 0, 1]) - 0.008
        rise = (made[:, -1, 1] - made[:, 0, 1]) * (1 if upper else -1)
        found += [bool(((out >= lids.LASH_ROOT_M[0] - 1e-9) & (out <= lids.LASH_ROOT_M[1] + 1e-9)).all()),
                  bool((rise > 0).all()), bool((made[:, -1, 2] > made[:, 0, 2]).all())]
    return found


def brows_follow_photo():
    """A brow whose photo is dark on its outer half only grows its hairs there (90 percent or more), each lying on
    the skin."""
    marks = lid_marks(30.0, 12.0)
    photo = np.full((200, 400, 3), 0.8)
    photo[35:66, 60:100] = 0.3  # the left brow's outer half (its inner end by the picture's middle, at 140 px)
    laid = lids.photo_frame(marks, LID_EYES, 0.006)
    points, triangles = grid_mesh(np.linspace(-0.07, 0.07, 71), np.linspace(-0.01, 0.05, 31),
                                  lambda x, y: 0.0 * x + 0.02)
    head = lids.front_view(points, triangles, lids.brow_box(marks["brows"][0], 0, laid), -1.0)
    hairs, _ = lids.brow_hairs(marks["brows"][0], 0, laid, lids.photo_lightness(photo), head,
                               np.random.default_rng(2))
    outer = laid(np.array([[100.0, 50.0]]), 0)[0, 0]
    share = float((hairs[:, 0, 0] < outer).mean()) if len(hairs) else 0.0
    lying = bool((np.abs(hairs[..., 2] - 0.02) < 0.001).all())
    return [bool(len(hairs) > 20 and share >= 0.9), lying]


def brow_painted_over():
    """The painted brow over an eye painted over with the skin round it (each texel within a tenth of the skin's
    colour), and the skin beside it left as it was."""
    points, triangles = grid_mesh(np.linspace(-0.06, 0.06, 121), np.linspace(-0.03, 0.06, 91),
                                  lambda x, y: 0.0 * x + 0.02)
    uv = np.column_stack([(points[:, 0] + 0.06) / 0.12, (points[:, 1] + 0.03) / 0.09])
    texture = np.ones((180, 240, 3)) * np.array(SKIN)
    rows, cols = np.mgrid[:180, :240]
    place_x, place_y = cols / 239 * 0.12 - 0.06, (179 - rows) / 179 * 0.09 - 0.03
    brow = (np.abs(place_x + 0.032) < 0.018) & (np.abs(place_y - 0.018) < 0.004)
    texture[brow] = (0.25, 0.18, 0.12)
    painted, count = lids.unpainted(points, triangles, uv, texture, LID_EYES)
    covered = np.abs(painted[brow] - np.array(SKIN)).max(axis=1) < 0.1 * np.array(SKIN).max()
    return [bool(count > 0 and covered.mean() > 0.98), bool(np.allclose(painted[~brow & (place_x > 0.0)], SKIN))]


def cloth_grid(rows=30, columns=30):
    """A flat grid (x right, y up, 1 cm apart) as triangles: (points, faces)."""
    x, y = np.meshgrid(np.arange(columns) * 0.01, np.arange(rows) * 0.01)
    points = np.stack([x.ravel(), y.ravel(), np.zeros(x.size)], 1)
    corner = (np.arange(rows - 1)[:, None] * columns + np.arange(columns - 1)[None]).ravel()
    faces = np.concatenate([np.stack([corner, corner + 1, corner + columns], 1),
                            np.stack([corner + 1, corner + columns + 1, corner + columns], 1)])
    return points, faces


def cloth_kinds_settled():
    """A grid painted jacket over jeans with a fleck of shirt in the jacket and a few jeans faces in it: after the
    vote and the islands, how many faces are of the wrong kind (0)."""
    points, faces = cloth_grid()
    middles = points[faces].mean(1)
    wanted = np.where(middles[:, 1] > 0.15, cloth.KINDS.index("jacket"), cloth.KINDS.index("jeans"))
    found = wanted.copy()
    found[np.flatnonzero(middles[:, 1] > 0.2)[[5, 40, 41, 300]]] = cloth.KINDS.index("shirt")
    found[np.flatnonzero(middles[:, 1] > 0.2)[[100, 230]]] = cloth.KINDS.index("jeans")
    free = np.ones(len(faces), bool)
    return int((cloth.islands_joined(faces, cloth.settled(faces, found, free), free) != wanted).sum())


def cloth_waistband():
    """A tube (radius 15 cm, 40 cm long) whose top loop is the jeans' top: each point's distance over its surface from
    that loop against its height under it (within 2 mm), and which ride (the band's width under the top)."""
    turns, rows = 60, 41
    angle, height = np.meshgrid(np.arange(turns) * 2 * np.pi / turns, np.arange(rows) * 0.01)
    points = np.stack([0.15 * np.cos(angle.ravel()), height.ravel(), 0.15 * np.sin(angle.ravel())], 1)
    corner = (np.arange(rows - 1)[:, None] * turns + np.arange(turns)[None]).ravel()
    right = (corner // turns) * turns + (corner + 1) % turns
    faces = np.concatenate([np.stack([corner, right, corner + turns], 1),
                            np.stack([right, right + turns, corner + turns], 1)])
    top = np.flatnonzero(points[:, 1] > 0.395)
    distance = cloth.over_surface(points, faces, top)
    under = 0.40 - points[:, 1]
    riding = distance < cloth.WAISTBAND_M
    return [bool(np.abs(distance - under).max() < 0.002), bool(np.all(riding == (under < cloth.WAISTBAND_M - 1e-9)))]


def cloth_walk_tiled():
    """A two-joint walk of 5 frames whose last repeats its first 0.3 m on: its cycle (4 frames, 0.3 m), and the
    tiled walk's tenth frame (the third cycle's second frame) 0.6 m on from the clip's second."""
    worlds = np.tile(np.eye(4), (5, 2, 1, 1))
    for frame in range(5):
        worlds[frame, :, 2, 3] = 0.075 * frame
        turn = np.radians(20.0 * np.sin(frame / 4 * 2 * np.pi))
        worlds[frame, 1, :3, :3] = [[np.cos(turn), -np.sin(turn), 0], [np.sin(turn), np.cos(turn), 0], [0, 0, 1]]
    length, travel = cloth.cycle_of(worlds)
    played, inside, cycle, _ = cloth.tiled(worlds, 12)
    moved = played[9, 0, 2, 3] - worlds[1, 0, 2, 3]
    return [length, round(float(travel[2]), 6), int(inside[9]), round(float(moved), 6)]


def cloth_body_pushed():
    """A body ball (radius 1) under a shell ball: pushed in to the margin under a shell 5 mm over it, never moved
    under a shell 10 cm over it, never outward."""
    ball = trimesh.creation.icosphere(subdivisions=3)
    found = []
    for shell_radius in (1.005, 1.1):
        moves = cloth.pushes(ball.vertices, ball.faces, ball.vertex_normals, ball.vertices * shell_radius,
                             ball.faces, cloth.MARGIN_M)
        inward = -np.einsum("pd,pd->p", moves, ball.vertex_normals)
        found.append(round(float(inward.mean()), 3))
    return found


def cloth_tube_laid():
    """A body column (radius 10 cm, 60 cm tall, closed) inside a two-walled garment tube (walls at 12.6 and 13 cm,
    40 cm tall, open at both ends) with a sliver and a speck off it: the sim mesh laid over the body and cleaned is one
    piece with two rims (the tube's ends), no edge on three faces, at the inner wall's radius."""
    turn = trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0))
    body = trimesh.creation.cylinder(radius=0.1, height=0.6, sections=48, transform=turn)
    walls = []
    for radius in (0.126, 0.13):
        wall = trimesh.creation.cylinder(radius=radius, height=0.4, sections=64, transform=turn)
        wall.update_faces(np.abs(wall.face_normals[:, 1]) < 0.5)  # the caps off: an open tube
        wall.remove_unreferenced_vertices()
        walls.append(wall)
    sliver = trimesh.Trimesh([[0.2, 0.0, 0.0], [0.2, 0.01, 0.0], [0.2, 0.02, 1e-12]], [[0, 1, 2]])
    speck = trimesh.Trimesh([[0.5, 0.0, 0.0], [0.5, 0.01, 0.0], [0.5, 0.0, 0.01]], [[0, 1, 2]])
    shell = trimesh.util.concatenate(walls + [sliver, speck])
    garment = np.arange(len(shell.faces))
    points, faces = cloth.cloth_mesh.laid_over((body.vertices, body.faces), np.zeros(len(body.vertices), int),
                                               (shell.vertices, shell.faces), garment, np.zeros(len(garment), int),
                                               (["Hips"], [-1]), edge=0.02)
    points, faces = cloth.cloth_mesh.cleaned(points, faces)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    shared = np.unique(edges, axis=0, return_counts=True)[1].max()
    radius = np.hypot(points[:, 0], points[:, 2])
    return [len(cloth.cloth_mesh.rims(faces)), len(np.unique(cloth.cloth_mesh.pieces_of(faces, len(points)))),
            int(shared), bool(np.abs(radius - 0.126).max() < 0.002)]


def cloth_mesh_mended():
    """A needle triangle in a grid collapsed (no corner under ANGLE_LEAST, the grid's other faces kept), and two
    triangles meeting at one point only made two fans (that point given twice)."""
    points, faces = cloth_grid(6, 6)
    points = np.vstack([points, [[0.0195, 0.0101, 0.0]]])  # half a millimetre off point 8: a needle to 13
    needle = int(np.flatnonzero((faces == 7).any(1) & (faces == 8).any(1) & (faces == 13).any(1))[0])
    faces = np.vstack([np.delete(faces, needle, axis=0), [[7, 36, 13], [36, 8, 13]]])
    mended_points, mended_faces = cloth.cloth_mesh.slivers_collapsed(points, faces)
    bow = cloth.cloth_mesh.fans_split(np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0.0]]),
                                      np.array([[0, 1, 2], [0, 3, 4]]))
    return [bool(cloth.cloth_mesh.corner_angles(mended_points, mended_faces).min() >= cloth.cloth_mesh.ANGLE_LEAST),
            len(mended_faces) >= len(faces) - 3, len(bow[0]), sorted(bow[1].ravel().tolist())]


def cloth_drawn_rides():
    """Points over and under a bent sheet bound to it move by none of the sheet's own move off its targets at rest and
    by all of a move the whole sheet makes off them; normals turn with their skinned turn (a zero one stays zero); a
    piece of the mesh with no riding point rides whole, one with a riding point keeps its loose."""
    points, faces = cloth_grid(8, 8)
    points[:, 2] = 0.3 * points[:, 0] ** 2
    render = np.random.default_rng(4).uniform([0.005, 0.005, -0.01], [0.065, 0.065, 0.01], (200, 3))
    binding = cloth.cloth_mesh.bound(render, points, faces)
    targets = np.stack([points, points + (0.0, 0.1, 0.0)])
    positions = np.stack([points, points + (0.0, 0.1, 0.03)])
    off = cloth.cloth_mesh.displaced(binding, positions, targets, faces)
    turn = trimesh.transformations.rotation_matrix(0.7, (0.3, 1.0, 0.2))
    moves = np.stack([np.eye(4), turn])[:, None]
    normals = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 0.0]])
    shaded = cloth.skinned_normals(normals, np.ones((2, 1)), moves)
    two = np.vstack([faces, faces + len(points)])
    riding = np.zeros(2 * len(points), bool)
    riding[0] = True
    anchored = cloth.anchored(two, riding)
    return [bool(np.abs(off[0]).max() < 1e-12), bool(np.abs(off[1] - (0.0, 0.0, 0.03)).max() < 1e-12),
            int(anchored[:len(points)].sum()), bool(anchored[len(points):].all()),
            bool(np.abs(shaded[1, 0] - turn[:3, 2]).max() < 1e-9), bool(np.abs(shaded[:, 1]).max() == 0.0)]

def cloth_jacket_off_legs():
    """[a face at the hips hanging from the hips may be jacket, the same face hanging from a thigh may not, a face
    under the wrist hanging from the hand may not], then under a long coat's hem at 0.6 m [the thigh's face at 0.92 m
    may, one at 0.7 m may, one at 0.5 m may not, the hand's may not]."""
    names = ["Hips", "Spine2", "Neck2", "Chest", "LeftFoot", "RightFoot", "LeftHand", "RightHand"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.15, 1.5, 1.3, 0.06, 0.06, 0.85, 0.85]
    person = {"names": names, "bind": bind}
    middles = np.array([[0.1, 0.92, 0.1], [0.1, 0.92, 0.1], [0.3, 0.8, 0.0]])
    short = cloth.allowed(person, middles, np.array(["Hips", "LeftLeg", "LeftHand"]))["jacket"].tolist()
    middles = np.array([[0.1, 0.92, 0.1], [0.1, 0.7, 0.1], [0.1, 0.5, 0.1], [0.3, 0.8, 0.0]])
    long = cloth.allowed(person, middles, np.array(["LeftLeg", "LeftLeg", "LeftLeg", "LeftHand"]), hem=0.6)
    return [short, long["jacket"].tolist()]


def cloth_shirt_round_neck():
    """[a face behind the neck 5 cm under Neck2 may be the T-shirt (a hood), one behind the chest 20 cm under it may
    not, one at the hood's height hanging from an upper arm may not, one in the open front at the chest may]
    (`allowed`: the garment under the jacket round the neck, ROUND_NECK_M)."""
    names = ["Hips", "Spine2", "Neck2", "Chest", "LeftFoot", "RightFoot", "LeftHand", "RightHand"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.15, 1.5, 1.3, 0.06, 0.06, 0.85, 0.85]
    person = {"names": names, "bind": bind}
    middles = np.array([[0.0, 1.45, -0.1], [0.0, 1.3, -0.1], [0.15, 1.45, 0.0], [0.0, 1.3, 0.1]])
    return cloth.allowed(person, middles, np.array(["Chest", "Chest", "LeftArm", "Chest"]))["shirt"].tolist()


def cloth_jeans_off_arms():
    """A jeans face whose points ride the hand wholly, half and half with the thigh, and the thigh, beside a laid
    hand's face (still_rig's hand part) sharing the last two (`cloth.jeans_off_arms`): [the hand's share at each of
    the four points]."""
    names = ["Hips", "LeftHand", "LeftLeg"]
    points = np.array([[0.0, 0.9, 0.0], [0.02, 0.9, 0.0], [0.04, 0.9, 0.0], [0.03, 0.88, 0.0], [0.0, 0.85, 0.0]])
    faces = np.array([[0, 1, 4], [1, 2, 3]])
    weights = np.array([[0.0, 1.0, 0.0], [0.0, 0.5, 0.5], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    person = {"names": names, "points": points, "faces": faces, "weights": weights, "hand": np.array([False, True])}
    kinds = np.array([cloth.KINDS.index("jeans"), cloth.KINDS.index("skin")])
    found = cloth.jeans_off_arms(person, kinds)
    return [round(float(found[number, 1]), 6) for number in (0, 1, 3, 4)]


def cloth_laid_hands_skin():
    """A person's laid hand (still_rig's hand part) whose wrist faces hang from the forearm and are painted the
    jacket's colour: [those faces' kinds are the skin's, the sleeve's are the jacket's] (`kinds_of` not taking the
    hand part as skin: the laid hands' wrists read as jacket and hung on its sim mesh)."""
    names = ["Hips", "Spine1", "Spine2", "Chest", "Neck2", "LeftArm", "LeftForeArm", "LeftHand", "LeftShin",
             "LeftFoot", "RightFoot", "RightArm", "RightForeArm", "RightHand", "RightShin"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.1, 1.15, 1.3, 1.5, 1.4, 1.05, 0.8, 0.45, 0.06, 0.06, 1.4, 1.05, 0.8, 0.45]
    bind[names.index("LeftArm"):names.index("LeftHand") + 1, 0, 3] = 0.3
    bind[names.index("RightArm"):names.index("RightHand") + 1, 0, 3] = -0.3
    places = ([("LeftArm", [0.3, 1.25 + 0.01 * k, 0.0], "jacket", False) for k in range(4)]
              + [("LeftShin", [0.1, 0.3 + 0.01 * k, 0.0], "jeans", False) for k in range(4)]
              + [("LeftHand", [0.3, 0.62 + 0.005 * k, 0.0], "skin", True) for k in range(3)]
              + [("LeftForeArm", [0.3, 0.80 + 0.01 * k, 0.0], "jacket", True) for k in range(3)])
    colour = {"jacket": [45.0, 10.0, 25.0], "jeans": [30.0, 0.0, -25.0], "skin": [70.0, 15.0, 18.0]}
    corner = np.array([[0.0, 0.0, 0.0], [0.004, 0.0, 0.0], [0.0, 0.004, 0.0]])
    points = np.concatenate([np.asarray(middle) + corner for _, middle, _, _ in places])
    faces = np.arange(len(points)).reshape(-1, 3)
    weights = np.zeros((len(points), len(names)))
    for number, (joint, _, _, _) in enumerate(places):
        weights[3 * number:3 * number + 3, names.index(joint)] = 1.0
    person = {"names": names, "bind": bind, "points": points, "faces": faces, "weights": weights,
              "lab": np.array([colour[kind] for _, _, kind, _ in places]),
              "head": np.zeros(len(faces), bool), "hand": np.array([hand for _, _, _, hand in places])}
    kinds = cloth.kinds_of(person)
    return [bool((kinds[-3:] == cloth.KINDS.index("skin")).all()),
            bool((kinds[:4] == cloth.KINDS.index("jacket")).all())]


def beard_chin_under_lip():
    """A face grid 6 cm wide from the nose 10 cm down whose beard rings one light piece from 3 to 7 cm under the nose
    (the lips and a pale chin under them, joined): [the lips 3.5 cm under the nose a hole, the chin 6 cm under it a
    hole, a cheek's beard face] (`beard.holes_in`)."""
    step = 0.002
    xs, ys = np.meshgrid(np.arange(-0.03, 0.03 + 1e-9, step), np.arange(0.0, -0.10 - 1e-9, -step))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    columns = xs.shape[1]
    faces = []
    for row in range(xs.shape[0] - 1):
        for column in range(columns - 1):
            corner = row * columns + column
            faces += [[corner, corner + 1, corner + columns], [corner + 1, corner + columns + 1, corner + columns]]
    faces = np.array(faces)
    middles = points[faces].mean(1)
    light = (np.abs(middles[:, 0]) < 0.02) & (middles[:, 1] < -0.03) & (middles[:, 1] > -0.07)
    frame = {"middle_x": 0.0, "nose": np.array([0.0, 0.0, 0.0])}
    holes = beard.holes_in(points, faces, ~light, np.ones(len(faces), bool), labels.adjacency(points, faces), frame)
    picks = [np.argmin(np.linalg.norm(middles - target, axis=1)) for target in
             ([0.0, -0.035, 0.0], [0.0, -0.06, 0.0], [0.025, -0.05, 0.0])]
    return [bool(holes[pick]) for pick in picks]


def cloth_nowhere_kind():
    """Faces painted as the jeans hanging from a forearm under the jacket's hem (TRELLIS.2's trousers fused to the
    arm: no kind's place allows them) beside a sleeve, a shin and a hand: [their kind is the jeans', never the
    head's] (`kinds_of`: argmin over no allowed kind gave KINDS' first, the head)."""
    names = ["Hips", "Spine1", "Spine2", "Chest", "Neck2", "LeftArm", "LeftForeArm", "LeftHand", "LeftShin",
             "LeftFoot", "RightFoot", "RightArm", "RightForeArm", "RightHand", "RightShin"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.1, 1.15, 1.3, 1.5, 1.4, 1.05, 0.8, 0.45, 0.06, 0.06, 1.4, 1.05, 0.8, 0.45]
    bind[names.index("LeftArm"):names.index("LeftHand") + 1, 0, 3] = 0.3
    bind[names.index("RightArm"):names.index("RightHand") + 1, 0, 3] = -0.3
    places = ([("LeftArm", [0.3, 1.25 + 0.01 * k, 0.0], "jacket") for k in range(4)]
              + [("LeftShin", [0.1, 0.3 + 0.01 * k, 0.0], "jeans") for k in range(4)]
              + [("LeftHand", [0.3, 0.62 + 0.005 * k, 0.0], "skin") for k in range(3)]
              + [("LeftForeArm", [0.2, 0.70 + 0.01 * k, 0.0], "jeans") for k in range(3)])
    colour = {"jacket": [45.0, 10.0, 25.0], "jeans": [30.0, 0.0, -25.0], "skin": [70.0, 15.0, 18.0]}
    corner = np.array([[0.0, 0.0, 0.0], [0.004, 0.0, 0.0], [0.0, 0.004, 0.0]])
    points = np.concatenate([np.asarray(middle) + corner for _, middle, _ in places])
    weights = np.zeros((len(points), len(names)))
    for number, (joint, _, _) in enumerate(places):
        weights[3 * number:3 * number + 3, names.index(joint)] = 1.0
    person = {"names": names, "bind": bind, "points": points, "faces": np.arange(len(points)).reshape(-1, 3),
              "weights": weights, "lab": np.array([colour[kind] for _, _, kind in places]),
              "head": np.zeros(len(places), bool), "hand": np.zeros(len(places), bool)}
    kinds = cloth.kinds_of(person)
    return [cloth.KINDS[kind] for kind in kinds[-3:]]


def cloth_hood_inside():
    """A sheet round the neck (40 x 40 cells, 1.2 to 1.6 m, hanging from the Chest; Neck2 at 1.5 m) of the T-shirt's
    kind with two jacket pieces of 200 faces in it: one wholly round the neck (over 1.38 m) and one reaching down to
    1.2 m: [the first is the T-shirt's, the second stays the jacket's] (`cloth.hood_inside`: the hood's shaded inside
    hung on the jacket's sim mesh)."""
    names = ["Hips", "Chest", "Neck2", "LeftArm", "RightArm"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.3, 1.5, 1.4, 1.4]
    grid = np.array([[0.01 * col, 1.2 + 0.01 * row, 0.0] for row in range(41) for col in range(41)])
    cells = [(row, col) for row in range(40) for col in range(40)]
    faces = np.array([face for row, col in cells for face in
                      ([row * 41 + col, row * 41 + col + 1, (row + 1) * 41 + col],
                       [row * 41 + col + 1, (row + 1) * 41 + col + 1, (row + 1) * 41 + col])])
    weights = np.zeros((len(grid), len(names)))
    weights[:, names.index("Chest")] = 1.0
    person = {"names": names, "bind": bind, "points": grid, "faces": faces, "weights": weights}
    kinds = np.full(len(faces), cloth.KINDS.index("shirt"))
    inside = np.array([(25 <= row < 35) and (5 <= col < 15) for row, col in cells for _ in range(2)])
    reaching = np.array([(row < 30) and (25 <= col < 29) and row >= 5 for row, col in cells for _ in range(2)])
    kinds[inside | reaching] = cloth.KINDS.index("jacket")
    found = cloth.hood_inside(person, kinds)
    return [cloth.KINDS[found[np.flatnonzero(inside)[0]]], cloth.KINDS[found[np.flatnonzero(reaching)[0]]]]


def cloth_fused_to_leg():
    """Faces hanging from a forearm under a jacket's hem at 0.8 m beside a thigh's face at 0.1 m across: one 7 cm
    from it, one 15 cm out (a hand held out beside the thigh), one over the hem: [True, False, False]
    (`cloth.fused_to_leg`; the hoodie man's lump faces before his thighs took the jacket and stretched to his hands
    as straps)."""
    middles = np.array([[0.1, 0.7, 0.0], [0.15, 0.7, 0.05], [0.25, 0.7, 0.0], [0.15, 0.85, 0.05]])
    strongest = np.array(["LeftLeg", "LeftForeArm", "LeftForeArm", "LeftForeArm"])
    return cloth.fused_to_leg(middles, strongest, 0.8)[1:].tolist()


def beard_density_read():
    """A 4 cm beard square's strands at the style's `beard_density_m2` (0.4e6) over those at beard.DENSITY: about
    their ratio, 0.5 (the style's density left unread: 1.0)."""
    square = np.array([[0.0, -0.1, 0.05], [0.04, -0.1, 0.05], [0.04, -0.06, 0.05], [0.0, -0.06, 0.05],
                       [1.0, 1.0, 1.0]])
    faces = np.array([[0, 1, 2], [0, 2, 3], [4, 4, 4]])
    bearded = np.array([True, True, False])
    normals = np.tile([0.0, 0.0, 1.0], (5, 1))
    frame = {"centre": np.zeros(3), "nose": np.array([0.0, 0.0, 0.1])}
    style = {"beard_length_m": 0.006, "beard_stubble_m": 0.002}
    counts = [len(beard.beard_strands(square, faces, bearded, normals, frame, given)[0])
              for given in ({**style, "beard_density_m2": 0.4e6}, style)]
    return round(counts[0] / counts[1], 1)


def cloth_hem_found():
    """A coat (a ring of radius 20 cm from 0.6 to 1.2 m, its paint the jacket's) over two legs (rings of 7 cm either
    side, from the floor to 1.0 m, their paint the jeans', so inside the coat they outnumber it): the hem read from
    0.9 m down, in metres (0.6), and read off every face of a band rather than its outermost (`outer_share` broken:
    under 0.9 m the legs outnumber the coat and the hem stays at its start)."""
    angles = np.linspace(0, 2 * np.pi, 120, endpoint=False)
    coat = [[0.2 * np.cos(a), y, 0.2 * np.sin(a)] for a in angles for y in np.arange(0.605, 1.2, 0.01)]
    legs = [[side * 0.09 + 0.07 * np.cos(a), y, 0.07 * np.sin(a)] for side in (-1, 1) for a in angles
            for y in np.arange(0.005, 1.0, 0.005)]
    middles = np.array(coat + legs)
    nearer = np.r_[np.ones(len(coat), bool), np.zeros(len(legs), bool)]
    clothes = np.ones(len(middles), bool)
    found = cloth.jacket_hem(middles, nearer, clothes, 0.9)
    band = np.abs(middles[:, 1] - 0.8) < 0.01
    return [round(found, 2), bool(nearer[band].mean() < cloth.HEM_SHARE)]


def cloth_scarf_split():
    """A front of a chest: a cream scarf (two strands 3 to 9 cm off the middle, 4 cm forward) over a black shirt (the
    middle 3 cm, behind it) inside a camel jacket: [the scarf's faces found, the shirt's found]; the same front with the
    two colours side by side at one depth (a hoodie's grey and its dark drawstrings) has no scarf."""
    names = ["Spine1", "Chest", "Neck2"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.05, 1.2, 1.5]
    xs, ys = np.meshgrid(np.arange(-0.105, 0.106, 0.005), np.arange(1.1, 1.45, 0.005))
    xs, ys = xs.ravel(), ys.ravel()
    scarf = (np.abs(xs) > 0.03) & (np.abs(xs) < 0.09)
    shirt = np.abs(xs) <= 0.03
    middles = np.r_[np.c_[xs, ys, np.where(scarf, 0.12, 0.08)], np.c_[np.full(400, 0.2), np.linspace(1.1, 1.4, 400),
                                                                     np.full(400, 0.05)]]
    lab = np.r_[np.where(scarf[:, None], [85.0, 1.0, 8.0], np.where(shirt[:, None], [5.0, 0.0, 0.0], [58.0, 13.0, 24.0])),
                np.tile([58.0, 13.0, 24.0], (400, 1))]
    jacket = np.r_[~scarf & ~shirt, np.ones(400, bool)]
    person = {"names": names, "bind": bind, "lab": lab, "head": np.zeros(len(middles), bool)}
    strongest = np.full(len(middles), "Chest")
    found = cloth.scarf_split(person, middles, strongest, {"jacket": jacket})
    flat = middles.copy()
    flat[:, 2] = np.where(jacket, flat[:, 2], 0.08)
    none = cloth.scarf_split(person, flat, strongest, {"jacket": jacket})
    return [bool(np.array_equal(found["scarf"][:len(xs)], scarf)), bool(np.array_equal(found["shirt"][:len(xs)], shirt)),
            none == {}]


def cloth_scarf_rides_round_neck():
    """A scarf hanging 37 cm down the chest from a turtleneck's collar (the shirt, its top 3 cm, over the chest joint),
    meeting no head or skin (a cut just under the chin keeps the body's own neck): [its top rides, its foot hangs]
    (read off the head and skin alone it rode nowhere, rode whole and the measures had no loose point)."""
    points, faces = cloth_grid(40, 10)
    points[:, 1] += 1.11
    names = ["Spine1", "Chest", "Neck1"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.05, 1.2, 1.45]
    kinds = np.where(points[faces].mean(1)[:, 1] > 1.47, cloth.KINDS.index("shirt"), cloth.KINDS.index("scarf"))
    person = {"points": points, "faces": faces, "names": names, "bind": bind}
    used, scarf_faces = cloth.garment_of(person, kinds, "scarf")
    riding = cloth.riding_of(person, kinds, "scarf", used, scarf_faces)
    heights = points[used, 1]
    return [bool(riding[heights > 1.45].all()), bool(~riding[heights < 1.3].any())]


def cloth_under_coloured():
    """A person painted a mid grey jacket (L 53.4: sRGB 0.5), a camel shirt (CIELAB 58, 13, 24) and black trousers:
    the body under them [the trunk the jacket's grey in linear RGB (0.214), the legs near black], and with no jacket
    [the trunk the shirt's camel] (the trunk's and legs' fixed white and denim showed as patches)."""
    kinds = np.array([cloth.KINDS.index(kind) for kind in ("jacket", "shirt", "jeans")])
    person = {"lab": np.array([[53.389, 0.0, 0.0], [58.0, 13.0, 24.0], [3.0, 0.0, 0.0]])}
    found = cloth.under_colours(person, kinds)
    shirt_only = cloth.under_colours(person, np.where(kinds == cloth.KINDS.index("jacket"),
                                                      cloth.KINDS.index("shirt"), kinds))
    return [bool(np.allclose(found[0], 0.214, atol=0.003)), bool(found[1].max() < 0.01),
            bool(shirt_only[0][0] > shirt_only[0][2] * 1.5)]


SKIRT_NAMES = ["Hips", "LeftLeg", "RightLeg", "Chest", "LeftArm", "LeftForeArm", "LeftHand", "RightArm",
               "RightForeArm", "RightHand"]


def skirt_person(points, faces, weights):
    """A toy person on SKIRT_NAMES: the hips at 1 m, the hip joints at 0.9 m 10 cm either side, the chest at 1.3 m,
    the shoulders (Arm joints) at 1.4 m 20 cm either side."""
    bind = np.repeat(np.eye(4)[None], len(SKIRT_NAMES), axis=0)
    places = {"Hips": (0, 1.0), "LeftLeg": (0.1, 0.9), "RightLeg": (-0.1, 0.9), "Chest": (0, 1.3),
              "LeftArm": (0.2, 1.4), "LeftForeArm": (0.2, 1.15), "LeftHand": (0.2, 0.9), "RightArm": (-0.2, 1.4),
              "RightForeArm": (-0.2, 1.15), "RightHand": (-0.2, 0.9)}
    for name, (x, y) in places.items():
        bind[SKIRT_NAMES.index(name), :2, 3] = x, y
    return {"names": SKIRT_NAMES, "bind": bind, "points": points, "faces": faces, "weights": weights}


def cloth_skirted():
    """A coat panel 40 cm wide from 1.1 m down to 0.5 m (1 cm apart), skinned to the hips over the hip joints (0.9 m)
    and to the thigh on its side under them, its outer lowest corner a cuff (on the left hand): under the hip joints its middle at
    the hem hangs from both thighs alike and from the pelvis (SKIRT_HIPS's hem share), its side (beyond its thigh)
    from its own thigh alone; over the hip joints and at the cuff the weights are
    their own, every row sums to one; a short jacket (all over 0.9 m) is left. A hand resting on the middle at 0.6 m
    (one point on the left hand) eases the skirt in over the surface: 2 cm under it a quarter of the skirt's (its
    pelvis 0.135 of the skirt's 0.54), so the coat by a swinging hand never tears (round 6)."""
    x, y = np.meshgrid(np.linspace(-0.2, 0.2, 41), np.linspace(0.5, 1.1, 61))
    points = np.round(np.c_[x.ravel(), y.ravel(), np.full(x.size, 0.1)], 6)
    corner = (np.arange(60)[:, None] * 41 + np.arange(40)[None]).ravel()
    faces = np.r_[np.c_[corner, corner + 1, corner + 42], np.c_[corner, corner + 42, corner + 41]]
    weights = np.zeros((len(points), len(SKIRT_NAMES)))
    weights[points[:, 1] >= 0.9, 0] = 1.0
    weights[(points[:, 1] < 0.9) & (points[:, 0] > 0), 1] = 1.0
    weights[(points[:, 1] < 0.9) & (points[:, 0] <= 0), 2] = 1.0
    cuff = int(np.flatnonzero((points[:, 0] == 0.2) & (points[:, 1] == 0.5))[0])
    weights[cuff] = 0.0
    weights[cuff, SKIRT_NAMES.index("LeftHand")] = 1.0
    resting = int(np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == 0.6))[0])
    weights[resting] = 0.0
    weights[resting, SKIRT_NAMES.index("LeftHand")] = 1.0
    kinds = np.full(len(faces), cloth.KINDS.index("jacket"))
    found = cloth.skirted(skirt_person(points, faces, weights), kinds)
    middle = int(np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == 0.5))[0])
    side = int(np.flatnonzero((points[:, 0] == -0.2) & (points[:, 1] == 0.5))[0])
    over = points[:, 1] >= 0.9
    short = np.where((points[faces][:, :, 1] >= 0.9).all(1), cloth.KINDS.index("jacket"), cloth.KINDS.index("jeans"))
    return [round(float(found[middle, 0]), 3), bool(np.isclose(found[middle, 1], found[middle, 2])),
            [round(float(value), 3) for value in found[side, :3]], bool(np.allclose(found[over], weights[over])),
            bool(np.allclose(found[cuff], weights[cuff])), bool(np.allclose(found.sum(1), 1.0)),
            bool(np.allclose(cloth.skirted(skirt_person(points, faces, weights), short), weights)),
            round(float(found[int(np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == 0.58))[0]), 0]), 3)]


def hem_turns_with_shoe():
    """A jeans leg panel 30 cm wide from 0.30 m down to 0.08 m (1 cm apart) skinned to the left shin, over a shoe panel
    from 0.07 m down to 0.0 m on the left foot (`cloth.hem_on_shoes`): the hem's lowest row takes the foot's weights
    (all but the 1 cm gap's third), a row 4 cm up keeps the shin's; every row sums to one."""
    x, y = np.meshgrid(np.linspace(-0.15, 0.15, 31), np.r_[np.linspace(0.0, 0.07, 8), np.linspace(0.08, 0.30, 23)])
    points = np.round(np.c_[x.ravel(), y.ravel(), np.zeros(x.size)], 6)
    corner = (np.arange(30)[:, None] * 31 + np.arange(30)[None]).ravel()
    faces = np.r_[np.c_[corner, corner + 1, corner + 32], np.c_[corner, corner + 32, corner + 31]]
    names = ["LeftShin", "LeftFoot"]
    weights = np.zeros((len(points), 2))
    weights[points[:, 1] >= 0.08, 0] = 1.0
    weights[points[:, 1] < 0.08, 1] = 1.0
    shoe = (points[faces][:, :, 1] <= 0.07).all(1)
    kinds = np.where(shoe, cloth.KINDS.index("shoes"), cloth.KINDS.index("jeans"))
    found = cloth.hem_on_shoes({"names": names, "points": points, "faces": faces, "weights": weights}, kinds)
    hem = int(np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == 0.08))[0])
    up = int(np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == 0.12))[0])
    return [round(float(found[hem, 1]), 3), round(float(found[up, 1]), 3), bool(np.allclose(found.sum(1), 1.0))]


def seam_held_to_shoe():
    """`hem_turns_with_shoe`'s jeans over its shoe (`cloth.seam_eased`): the hem's row on the shoe takes none of the
    cloth's move, the row 1 cm up a third, the row 5 cm up all of it."""
    x, y = np.meshgrid(np.linspace(-0.15, 0.15, 31), np.r_[np.linspace(0.0, 0.07, 8), np.linspace(0.08, 0.30, 23)])
    points = np.round(np.c_[x.ravel(), y.ravel(), np.zeros(x.size)], 6)
    corner = (np.arange(30)[:, None] * 31 + np.arange(30)[None]).ravel()
    faces = np.r_[np.c_[corner, corner + 1, corner + 32], np.c_[corner, corner + 32, corner + 31]]
    shoe = (points[faces][:, :, 1] <= 0.07).all(1)
    kinds = np.where(shoe, cloth.KINDS.index("shoes"), cloth.KINDS.index("jeans"))
    used, own = cloth.garment_of({"faces": faces}, kinds, "jeans")
    share = cloth.seam_eased({"points": points, "faces": faces}, kinds, "jeans", used, own)
    rows = [int(np.flatnonzero(used == np.flatnonzero((points[:, 0] == 0.0) & (points[:, 1] == height))[0])[0])
            for height in (0.07, 0.08, 0.12)]
    return [round(float(share[row]), 2) for row in rows]


def grid_sheet(count=21, spacing=0.01):
    """A flat sheet of count x count points `spacing` apart (z 0) and its triangles."""
    x, y = np.meshgrid(np.arange(count) * spacing, np.arange(count) * spacing)
    points = np.c_[x.ravel(), y.ravel(), np.zeros(x.size)]
    corner = (np.arange(count - 1)[:, None] * count + np.arange(count - 1)[None]).ravel()
    faces = np.r_[np.c_[corner, corner + 1, corner + count + 1], np.c_[corner, corner + count + 1, corner + count]]
    return points, faces


def jeans_weights_smoothed():
    """A jeans sheet over a row of shoe faces, each point's shin and foot shares speckled 0 to 0.3 apart from its
    neighbours (`cloth.weights_smoothed`): the jeans' own points' shares within a tenth of the speckle of their
    neighbours', the points the shoes share kept, every row summing to one."""
    points, faces = grid_sheet()
    rng = np.random.default_rng(4)
    foot = rng.uniform(0.0, 0.3, len(points))
    weights = np.c_[1.0 - foot, foot]
    shoe = points[faces].mean(1)[:, 1] < 0.02
    kinds = np.where(shoe, cloth.KINDS.index("shoes"), cloth.KINDS.index("jeans"))
    found = cloth.weights_smoothed({"points": points, "faces": faces, "weights": weights}, kinds, "jeans")
    shared = np.zeros(len(points), bool)
    shared[faces[shoe].ravel()] = True
    edges = faces[~shoe][:, [0, 1]]
    edges = edges[~shared[edges].any(1)]
    return [bool(np.abs(found[edges[:, 0], 1] - found[edges[:, 1], 1]).mean()
                 < np.abs(weights[edges[:, 0], 1] - weights[edges[:, 1], 1]).mean() / 10),
            bool(np.allclose(found[shared], weights[shared])), bool(np.allclose(found.sum(1), 1.0))]


def cloth_short_edge_collapsed():
    """A tiny triangle of 1 mm sides set in a 1 cm hexagon (no corner under ANGLE_LEAST) collapsed: no edge under
    3 mm is left (the hoodie man's jeans kept a 1 mm edge, read as a stretch of 0.68)."""
    ring = np.array([[np.cos(angle), np.sin(angle), 0.0] for angle in np.arange(6) * np.pi / 3]) * 0.01
    inner = np.array([[np.cos(angle), np.sin(angle), 0.0] for angle in np.arange(3) * 2 * np.pi / 3]) * 0.000577
    points = np.r_[ring, inner]
    faces = [[6, 7, 8]]
    for side in range(6):
        near = 6 + (side // 2)
        faces.append([side, (side + 1) % 6, near if side % 2 == 0 else 6 + ((side + 1) // 2) % 3])
    for inner_point in range(3):
        faces.append([6 + inner_point, 6 + (inner_point + 1) % 3, (2 * inner_point + 1) % 6])
    mesh = trimesh.Trimesh(points, np.array(faces), process=False)
    trimesh.repair.fix_winding(mesh)
    before = cloth.cloth_mesh.corner_angles(points, np.asarray(mesh.faces)).min()
    mended, mended_faces = cloth.cloth_mesh.slivers_collapsed(points, np.asarray(mesh.faces))
    return [bool(before >= cloth.cloth_mesh.ANGLE_LEAST),
            bool(cloth.cloth_mesh.edge_lengths(mended, mended_faces).min() >= 0.003)]


def cloth_paint_read_from_top():
    """A picture red in its top half and blue in its bottom, read at a face whose glTF texture places lie near the
    top (v 0.1, glTF's v runs down): red, not blue (`file_places` left out: every face read its mirror row)."""
    picture = np.zeros((8, 8, 3))
    picture[:4, :, 0] = 1.0
    picture[4:, :, 2] = 1.0
    places = cloth.file_places(np.array([[0.4, 0.1], [0.6, 0.1], [0.5, 0.15]]))
    lab = cloth.face_paint(picture, places, np.array([[0, 1, 2]]))[0]
    return bool(lab[1] > 50 and lab[2] > 30)


def colour_toy():
    """A toy front (points on a plane facing +z, 0.6 m by 1.2 m, UV its box) painted as TRELLIS.2 paints, and its photo
    (RGBA, a margin of air round the person): (points, uv, paint texture, photo)."""
    xs, ys = np.meshgrid(np.linspace(0.0, 0.6, 150), np.linspace(0.0, 1.2, 300))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    uv = np.column_stack([xs.ravel() / 0.6, ys.ravel() / 1.2])
    height = 1.0 - (np.arange(128) + 0.5) / 128  # the texture's rows, top down, as heights
    paint = np.zeros((128, 64, 4), np.uint8)
    paint[..., 3] = 255
    fold = (np.arange(128) // 6) % 2 == 1
    paint[height > 0.5, :, :3] = (65, 72, 68)
    paint[(height > 0.5) & fold, :, :3] = (48, 54, 51)
    paint[(height <= 0.5) & (height > 0.1), :, :3] = (7, 7, 8)
    paint[height <= 0.1, :, :3] = (14, 3, 0)
    grain = np.random.default_rng(2).integers(-5, 6, paint[..., :3].shape)  # boots, trousers overlap
    paint[..., :3] = np.clip(paint[..., :3].astype(int) + grain, 0, 255).astype(np.uint8)
    photo = np.zeros((280, 160, 4), np.uint8)
    rows = 1.0 - (np.arange(240) + 0.5) / 240
    person = photo[20:260, 20:140]
    person[..., 3] = 255
    person[rows > 0.5, :, :3] = (131, 137, 123)
    person[(rows <= 0.5) & (rows > 0.1), :, :3] = (15, 15, 21)
    person[rows <= 0.1, :, :3] = (89, 51, 41)
    noise = np.random.default_rng(3).integers(-3, 4, person[..., :3].shape)
    person[..., :3] = np.clip(person[..., :3].astype(int) + noise, 0, 255).astype(np.uint8)
    return points, uv, paint, photo


def colour_body_toy():
    """A toy bust as `colour_toy`'s front: (points, uv, paint, photo, the paint's texture rows as heights)."""
    xs, ys = np.meshgrid(np.linspace(0.0, 0.6, 150), np.linspace(0.0, 1.2, 300))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    uv = np.column_stack([xs.ravel() / 0.6, ys.ravel() / 1.2])
    height = 1.0 - (np.arange(128) + 0.5) / 128
    paint = np.zeros((128, 64, 4), np.uint8)
    paint[..., 3] = 255
    paint[height > 0.9, :, :3] = (47, 37, 32)
    paint[(height <= 0.9) & (height > 0.6), :32, :3] = (166, 109, 99)
    paint[(height <= 0.9) & (height > 0.6), 32:, :3] = (55, 39, 35)
    paint[height <= 0.6, :, :3] = (65, 72, 68)
    grain = np.random.default_rng(2).integers(-3, 4, paint[..., :3].shape)
    paint[..., :3] = np.clip(paint[..., :3].astype(int) + grain, 0, 255).astype(np.uint8)
    photo = np.zeros((280, 160, 4), np.uint8)
    rows = 1.0 - (np.arange(240) + 0.5) / 240
    person = photo[20:260, 20:140]
    person[..., 3] = 255
    person[rows > 0.9, :, :3] = (36, 28, 23)
    person[(rows <= 0.9) & (rows > 0.6), :, :3] = (208, 158, 137)
    person[rows <= 0.6, :, :3] = (131, 137, 123)
    noise = np.random.default_rng(3).integers(-3, 4, person[..., :3].shape)
    person[..., :3] = np.clip(person[..., :3].astype(int) + noise, 0, 255).astype(np.uint8)
    return points, uv, paint, photo, height


def colour_body_kept():
    """The toy bust toned: its hair, the face's skin half and its dark half each within 2 Lab units of their paint;
    the jacket within 6 of the photo's sage."""
    from skimage.color import rgb2lab
    points, uv, paint, photo, height = colour_body_toy()
    centres, table, _ = colour.fitted(points, colour.texel_colours(paint, uv), photo)
    before = rgb2lab(paint[..., :3] / 255.0)
    after = rgb2lab(colour.toned_texture(paint, colour.heights_of(points), uv, centres, table)[..., :3] / 255.0)
    face = (height < 0.88) & (height > 0.62)

    def moved(rows, columns):
        return float(np.linalg.norm(after[rows][:, columns].reshape(-1, 3).mean(0)
                                    - before[rows][:, columns].reshape(-1, 3).mean(0)))

    sage = rgb2lab(np.array([[[131, 137, 123]]], float) / 255.0)[0, 0]
    jacket = float(np.linalg.norm(after[height < 0.55].reshape(-1, 3).mean(0) - sage))
    return [moved(height > 0.92, slice(None)) < 2.0, moved(face, slice(2, 30)) < 2.0,
            moved(face, slice(34, 62)) < 2.0, jacket < 6.0]


def colour_toned():
    """The toy's paint toned toward its photo: the jacket, trousers and boots within 6 Lab units of the photo's (the
    boots' trace of red never lost to the trousers), and the jacket's fold stripes keeping over half their depth."""
    from skimage.color import rgb2lab
    points, uv, paint, photo = colour_toy()
    centres, table, _ = colour.fitted(points, colour.texel_colours(paint, uv), photo)
    toned = rgb2lab(colour.toned_texture(paint, colour.heights_of(points), uv, centres, table)[..., :3] / 255.0)
    height = 1.0 - (np.arange(128) + 0.5) / 128
    fold = (np.arange(128) // 6) % 2 == 1

    def lab_of(rgb):
        return rgb2lab(np.array(rgb, float)[None, None] / 255.0)[0, 0]

    def off(rows, rgb):
        return float(np.linalg.norm(toned[rows].reshape(-1, 3).mean(0) - lab_of(rgb)))

    jacket, flat = height > 0.55, (height > 0.55) & ~fold
    depth_before = lab_of((65, 72, 68))[0] - lab_of((48, 54, 51))[0]
    depth_after = toned[flat].reshape(-1, 3)[:, 0].mean() - toned[jacket & fold].reshape(-1, 3)[:, 0].mean()
    return [off(jacket, (131, 137, 123)) < 6.0, off((height < 0.45) & (height > 0.15), (15, 15, 21)) < 6.0,
            off(height < 0.06, (89, 51, 41)) < 6.0, bool(depth_after > 0.5 * depth_before)]


def colour_two_parts():
    """The toy front as a swapped model's two textured primitives (its left half on the paint, its right half on the
    paint at twice the size), toned through the file: each picture keeps its size and each half's jacket reads within
    6 Lab units of the photo's sage."""
    import pathlib
    import tempfile
    from PIL import Image
    from skimage.color import rgb2lab
    from tools.props import glb_file
    points, uv, paint, photo = colour_toy()
    grid = np.arange(points.shape[0]).reshape(300, 150)
    scene = trimesh.Scene()
    halves = (("left", slice(0, 75), paint), ("right", slice(74, 150), paint.repeat(2, 0).repeat(2, 1)))
    for name, columns, picture in halves:
        block = grid[:, columns]
        corners = block[:-1, :-1].ravel(), block[:-1, 1:].ravel(), block[1:, :-1].ravel(), block[1:, 1:].ravel()
        triangles = np.vstack([np.column_stack([corners[0], corners[1], corners[3]]),
                               np.column_stack([corners[0], corners[3], corners[2]])])
        used = np.unique(triangles)
        mesh = trimesh.Trimesh(points[used], np.searchsorted(used, triangles), process=False)
        material = trimesh.visual.material.PBRMaterial(name=name, baseColorTexture=Image.fromarray(picture))
        mesh.visual = trimesh.visual.TextureVisuals(uv=uv[used], material=material)
        scene.add_geometry(mesh, geom_name=name)
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        scene.export(folder / "model.glb")
        Image.fromarray(photo).save(folder / "photo.png")
        colour.toned(folder / "model.glb", folder / "photo.png", folder / "toned.glb", folder / "colour.json")
        document, views = glb_file.read(folder / "toned.glb")
        parts = colour.parts_of(document, views)
        pictures = [colour.picture_of(document, views, image) for _, _, image in parts]
    sage = rgb2lab(np.array([[[131, 137, 123]]], float) / 255.0)[0, 0]
    jackets = [rgb2lab(colour.texel_colours(picture, part_uv)[part_points[:, 1] > 0.7]).mean(0)
               for (part_points, part_uv, _), picture in zip(parts, pictures)]
    return [[picture.shape[:2] for picture in pictures], [bool(np.linalg.norm(jacket - sage) < 6.0) for jacket in jackets]]


def tether_curtain():
    """A curtain (30 cm square, 2 cm apart, its top row riding) swung 2.5 cm toward and away from a ball behind it,
    as tethered cloth feeling g toward the ball (its limb turned a quarter): [its riding row on its targets, every point
    within its tether, no point deeper toward the ball than its target or half a millimetre past the clearance, the
    loose cloth hanging over a centimetre off its targets, no edge stretched past 5%]."""
    xs, ys = np.meshgrid(np.linspace(-0.15, 0.15, 16), np.linspace(0.0, -0.3, 16))
    points = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    grid = np.arange(256).reshape(16, 16)
    corners = grid[:-1, :-1].ravel(), grid[:-1, 1:].ravel(), grid[1:, :-1].ravel(), grid[1:, 1:].ravel()
    faces = np.vstack([np.column_stack([corners[0], corners[2], corners[1]]),
                       np.column_stack([corners[1], corners[2], corners[3]])])
    riding = np.zeros(256, bool)
    riding[:16] = True
    ball = trimesh.creation.icosphere(3, 0.1)
    centre = np.array([0.0, -0.25, -0.13])
    frames = 45
    targets = np.repeat(points[None], frames, axis=0)
    targets[:, :, 2] -= 0.025 * np.sin(np.arange(frames) / 30.0 * 4.0 * np.pi)[:, None]
    body = np.repeat((np.asarray(ball.vertices) + centre)[None], frames, axis=0)
    tether = cloth_tether.tethers(cloth_tether.TETHER_M["jeans"], -points[:, 1])
    least = cloth_tether.allowances(targets, body, np.asarray(ball.faces), 0.0015)
    run = cloth_tether.tethered(targets, tether, faces, body, np.asarray(ball.faces), 30.0, least,
                                np.tile([0.0, 0.0, -9.81], (frames, 256, 1)))

    def depth(positions):
        return 0.1 - np.linalg.norm(positions - centre, axis=2)

    edges = cloth_tether.edges_of(faces)
    built = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    now = np.linalg.norm(run[:, edges[:, 0]] - run[:, edges[:, 1]], axis=2)
    return [float(np.abs(run[:, riding] - targets[:, riding]).max()) == 0.0,
            bool((np.linalg.norm(run - targets, axis=2) - tether).max() < 1e-9),
            bool((depth(run) - np.maximum(depth(targets), -0.0015)).max() < 0.0005),
            bool(np.linalg.norm(run - targets, axis=2).max() > 0.01), bool((now / built - 1.0).max() < 0.05)]


def tether_gravity():
    """The gravity a point feels beyond its rest hang (m/s^2), its limb unturned, turned a quarter and turned over."""
    moves = np.repeat(np.eye(4)[None, None], 3, axis=0)
    moves[1, 0, :3, :3] = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    moves[2, 0, :3, :3] = np.diag([-1.0, -1.0, 1.0])
    felt = cloth_tether.turned_gravity(np.ones((1, 1)), moves)[:, 0]
    return [round(float(np.linalg.norm(force)), 2) for force in felt]


def person_hair_removed():
    """The hair step's removed triangles read back from kept.glb's faces (`person.removed_faces`)."""
    faces = np.random.default_rng(3).integers(0, 50, (40, 3))
    taken = np.zeros(40, bool)
    taken[[1, 7, 8, 30]] = True
    return np.flatnonzero(person.removed_faces(faces, faces[~taken])).tolist()


def neck_fans_found():
    """A neck tube open at the cut (the swapped model's points) and a rig made of its faces, a fan from the cut loop's
    middle, one from a loop far under it (an armpit's), and one from a loop along the tube's front just under the cut
    and back round a collar over it, its middle on the model (a hood layer kept there): `person.neck_fans` finds the
    cut's fan and the whole collar fan, those faces lying along the tube too (the tube's kept, the armpit's kept)."""
    angles = np.linspace(0.0, 2.0 * np.pi, 48, endpoint=False)
    heights = np.linspace(0.0, 0.2, 41)
    ring = np.stack([np.cos(angles) * 0.05, np.zeros(48), np.sin(angles) * 0.05], -1)
    tube = np.concatenate([ring + (0.0, height, 0.0) for height in heights])
    faces = []
    for level in range(40):
        for step in range(48):
            first, second = level * 48 + step, level * 48 + (step + 1) % 48
            faces += [[first, second, second + 48], [first, second + 48, first + 48]]
    tube_faces = tube[np.array(faces)]
    cut_ring = ring + (0.0, 0.2, 0.0)
    cut_fan = np.stack([cut_ring, np.roll(cut_ring, -1, 0), np.tile((0.0, 0.2, 0.0), (48, 1))], 1)
    low_ring = ring * 0.6 + (0.3, -0.2, 0.0)
    low_fan = np.stack([low_ring, np.roll(low_ring, -1, 0), np.tile((0.3, -0.2, 0.0), (48, 1))], 1)
    wedge = np.array([[[0.05, 0.3, 0.0], [0.09, 0.33, 0.03], [0.1, 0.36, -0.02]]])  # out under the hair, over the band
    turns = np.linspace(-np.pi / 2, np.pi / 2, 13)
    loop = np.concatenate([np.stack([np.sin(turns) * 0.05, np.full(13, 0.19), np.cos(turns) * 0.05], -1),
                           np.stack([np.sin(turns[::-1]) * 0.09, np.full(13, 0.23), np.cos(turns[::-1]) * 0.09], -1)])
    collar_fan = np.stack([loop, np.roll(loop, -1, 0), np.tile(loop.mean(0), (len(loop), 1))], 1)
    around = np.linspace(-np.pi, np.pi, 200)
    collar = np.stack([np.sin(around) * 0.09, np.full(200, 0.23), np.cos(around) * 0.09], -1)
    swapped = np.concatenate([tube, low_ring, collar, loop.mean(0)[None]])
    found = person.neck_fans(swapped, np.eye(4), 0.2, 1.7,
                             np.concatenate([tube_faces, cut_fan, low_fan, wedge, collar_fan]))
    rest = len(tube_faces) + 97
    return [int(found[len(tube_faces):len(tube_faces) + 48].sum()), int(found[:len(tube_faces)].sum()),
            int(found[len(tube_faces) + 48:rest - 1].sum()), int(found[rest - 1]), int(found[rest:].sum())]


def neck_off_the_head():
    """Five points' weights over Chest, Neck1, Neck2 and the Head (the chain's joints 0.2 and 0.03 under the cut and
    at it): `person.neck_chained` moves the Head's share under the cut onto the chain by height, all of it at
    Neck1's height 0.03 under the cut (onto Neck1), half of it 0.01 under (onto Neck1 and Neck2 by height), none at
    the cut or over it, and leaves a nape's point hanging from no Head as it was: [each point's weights, rounded]."""
    weights = np.array([[0.6, 0.0, 0.0, 0.4], [0.0, 0.5, 0.0, 0.5], [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0],
                        [1.0, 0.0, 0.0, 0.0]])
    over = np.array([-0.03, -0.01, 0.0, 0.01, -0.03])  # NECK_UNDER 0.02
    chained = person.neck_chained(weights, over, 3, [0, 1, 2], np.array([-0.2, -0.03, 0.0]))
    return np.round(chained, 3).tolist()


def head_edge_skirted():
    """A neck tube open at its foot (the head's edge at the cut) and closed nowhere else: `head_swap.skirt` hangs one
    copy of each foot point 1.3 cm down and 5 mm in and joins each open edge to its copies by two triangles facing
    out as the tube does: [new faces, the copies' lowest, their farthest from the axis, the share facing out]."""
    angles = np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)
    ring = np.stack([np.cos(angles) * 0.05, np.sin(angles) * 0.05, np.zeros(24)], -1)
    points = np.concatenate([ring + (0.0, 0.0, height) for height in (0.0, 0.01, 0.02)])
    faces = np.array([face for level in range(2) for step in range(24) for face in
                      ([level * 24 + step, level * 24 + (step + 1) % 24, 24 + level * 24 + (step + 1) % 24],
                       [level * 24 + step, 24 + level * 24 + (step + 1) % 24, 24 + level * 24 + step])])
    copies, _, made = head_swap.skirt(points, faces, points[:, 2] < 0.005, (0.0, 0.0, -1.0), 0.013, 0.005)
    corners = np.r_[points, copies][made]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    out = np.einsum("ij,ij->i", normals[:, :2], corners.mean(axis=1)[:, :2]) > 0
    return [len(made), round(float(copies[:, 2].min()), 4), round(float(np.hypot(*copies[:, :2].T).max()), 4),
            float(out.mean())]


def skirt_landed_neck_level():
    """The neck's photo skin, the skirt's landing and the level cut: [the lower face's points read (under the jaw, the
    face, the face with half a share, over the band), all photo points read when the face shows under
    NECK_PHOTO_LEAST, the copies landed (the near on its found point, the far and the unfound left), a point on the
    level plane at its height and its normal pointing up]."""
    heights = np.r_[np.full(120, 0.05), 0.01, 0.05, 0.1]
    share = np.r_[np.ones(120), 1.0, 0.5, 1.0]
    face = head_swap.photo_on_face(heights, share)
    few = head_swap.photo_on_face(heights[110:], share[110:])
    copies = np.zeros((3, 3))
    found = np.array([[0.0, 0.0, 0.004], [0.0, 0.0, 0.03], [9.0, 9.0, 9.0]])
    landed = head_swap.landed(copies, found, [0.004, 0.03, np.inf], 0.02)
    turn = np.array([[0.0, 0.0, 2.0], [0.0, 0.5, 0.0], [-2.0, 0.0, 0.0]])
    point, normal = head_swap.level_plane(turn, np.array([0.1, 0.3, -0.2]), 0.8)
    return [face[-4:].tolist(), int(few.sum()), bool(np.allclose(landed, [found[0], copies[1], copies[2]])),
            bool(np.isclose((turn @ point)[1] + 0.3, 0.8)), bool((turn @ (point + normal))[1] + 0.3 > 0.8)]


def neck_roles_read():
    """A swapped model's head (a neck tube from the cut up) and body (a neck tube under it and a collar ring 9 cm out
    over the cut), the head model's hair and skin middles beside the head: [the collar's face released, the head's
    neck not, the body 40 cm under the cut not; a head face on the hair read as the hair, one on the skin not]."""
    angles = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    ring = np.stack([np.cos(angles), np.zeros(64), np.sin(angles)], -1)
    head = np.concatenate([ring * 0.05 + (0.0, height, 0.0) for height in np.linspace(0.2, 0.3, 21)])
    body = np.concatenate([ring * radius + (0.0, height, 0.0) for radius, heights in
                           ((0.05, np.linspace(-0.3, 0.2, 101)), (0.09, np.linspace(0.2, 0.24, 9)))
                           for height in heights])
    middles = np.array([[0.09, 0.22, 0.0], [0.05, 0.25, 0.0], [0.05, -0.2, 0.0], [0.0, 0.28, 0.05],
                        [0.0, 0.28, -0.05]])
    hair, skin = np.array([[0.0, 0.281, 0.051]]), np.array([[0.0, 0.281, -0.051]])
    released, on_hair = person.neck_roles(head, body, np.eye(4), 0.2, 1.7, middles, hair, skin)
    return released[:3].tolist() + on_hair[3:].tolist()


def cloth_neck_released():
    """Four faces of still_rig's head part at the chest's height (strongest on the Chest) and a few hair faces over
    them: released and painted as the jacket, as the hair and as the skin, and one painted as the jacket never
    released; and a face outside the head part on the upper arm painted as the skin, released (a scarf over the
    shoulder): [their kinds]."""
    names = ["Hips", "Spine1", "Spine2", "Chest", "Neck2", "LeftArm", "LeftForeArm", "LeftHand", "LeftShin",
             "LeftFoot", "RightFoot", "RightArm", "RightForeArm", "RightHand", "RightShin"]
    bind = np.repeat(np.eye(4)[None], len(names), axis=0)
    bind[:, 1, 3] = [1.0, 1.1, 1.15, 1.3, 1.5, 1.4, 1.05, 0.8, 0.45, 0.06, 0.06, 1.4, 1.05, 0.8, 0.45]
    bind[names.index("LeftArm"):names.index("LeftHand") + 1, 0, 3] = 0.3
    colour = {"jacket": [45.0, 10.0, 25.0], "jeans": [30.0, 0.0, -25.0], "skin": [70.0, 15.0, 18.0],
              "hair": [12.0, 3.0, 3.0]}
    places = ([("LeftArm", [0.3, 1.25 + 0.01 * k, 0.0], "jacket", "") for k in range(4)]
              + [("LeftShin", [0.1, 0.3 + 0.01 * k, 0.0], "jeans", "") for k in range(4)]
              + [("LeftHand", [0.3, 0.62 + 0.005 * k, 0.0], "skin", "hand") for k in range(3)]
              + [("Neck2", [0.0, 1.6 + 0.01 * k, -0.05], "hair", "hair") for k in range(3)]
              + [("Chest", [0.05 * k, 1.45, -0.05], kind, "released") for k, kind in
                 enumerate(("jacket", "hair", "skin"))]
              + [("Chest", [0.15, 1.45, -0.05], "jacket", "head")]
              + [("LeftArm", [0.3, 1.32, 0.0], "skin", "outside")])
    corner = np.array([[0.0, 0.0, 0.0], [0.004, 0.0, 0.0], [0.0, 0.004, 0.0]])
    points = np.concatenate([np.asarray(middle) + corner for _, middle, _, _ in places])
    faces = np.arange(len(points)).reshape(-1, 3)
    weights = np.zeros((len(points), len(names)))
    for number, (joint, _, _, _) in enumerate(places):
        weights[3 * number:3 * number + 3, names.index(joint)] = 1.0
    role = np.array([role for _, _, _, role in places])
    person = {"names": names, "bind": bind, "points": points, "faces": faces, "weights": weights,
              "lab": np.array([colour[kind] for _, _, kind, _ in places]),
              "head": np.isin(role, ("hair", "released", "head")), "hand": role == "hand"}
    kinds = cloth.kinds_of(person, np.isin(role, ("released", "outside")), role == "hair")
    return [cloth.KINDS[kind] for kind in kinds[-5:]]


def old_hair_painted_over():
    """A jacket face and a neck's skin face, each with a face of the body's old hair beside it (released and kept the
    head), and a head face never released nearer the second old hair than the skin face: [the old hair's and the head
    face's kinds, which faces are painted over, the joint weighting the first old hair's own point]."""
    points = np.array([[0.0, 0.0, 0.0], [0.01, 0.0, 0.0], [0.0, 0.01, 0.0],        # jacket
                       [0.011, 0.011, 0.0], [0.02, 0.0, 0.0],                       # old hair on it (shares point 1)
                       [0.47, 0.0, 0.0], [0.48, 0.0, 0.0], [0.47, 0.01, 0.0],      # skin
                       [0.51, 0.011, 0.0], [0.52, 0.0, 0.0], [0.52, 0.01, 0.0],    # old hair beside it
                       [0.52, 0.02, 0.0], [0.53, 0.02, 0.0], [0.52, 0.03, 0.0]])   # head
    faces = np.array([[0, 1, 2], [1, 3, 4], [5, 6, 7], [8, 9, 10], [11, 12, 13]])
    joint = np.array([0, 0, 0, 2, 2, 1, 1, 1, 2, 2, 2, 2, 2, 2])
    head, jacket, skin = (cloth.KINDS.index(kind) for kind in ("head", "jacket", "skin"))
    person = {"points": points, "faces": faces, "weights": np.eye(3)[joint]}
    kinds, over, weights = cloth.painted_over(person, np.array([jacket, head, skin, head, head]),
                                              np.array([True, True, True, True, False]))
    return [cloth.KINDS[kind] for kind in kinds[[1, 3, 4]]], over.tolist(), int(weights[3].argmax())


def old_hair_repainted():
    """A garment's square (z 0, its texture places the picture's left half, whose red rises with u) and a face of old
    hair 1 cm over it (its own places in the dark right half) repainted (`painted.repainted`): [its texels' red the
    garment's at their nearest points (within 1e-6), that red not one flat paint (spread over 0.02), a triangle smaller
    than a texel given texels, a dark paint among sage ones not read as the garment's (`painted.kind_like`)]."""
    size = 32
    picture = np.zeros((size, size, 3))
    picture[..., 0] = ((np.arange(size) + 0.5) / size)[None, :]
    picture[..., 1:] = 0.5
    picture[:, size // 2:] = (0.1, 0.05, 0.05)
    square = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
                       [[0.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]])
    square_places = square[..., :2] * np.array([0.5, 1.0])

    def nearest(points):
        located = np.clip(points, 0.0, 1.0) * np.array([1.0, 1.0, 0.0])
        return located, (located[:, 0] < located[:, 1]).astype(int)
    over = np.array([[[0.3, 0.4, 0.01], [0.6, 0.4, 0.01], [0.3, 0.6, 0.01]]])
    places = np.array([[[0.7, 0.5], [0.8, 0.5], [0.7, 0.6]]])
    painted_picture, count = painted.repainted(picture, places, over, square, square_places, nearest,
                                               lambda found, triangle: painted.bilinear(picture, found))
    rows, columns, _, weights = painted.texels(places, (size, size))
    wanted = 0.5 * np.clip(weights @ over[0], 0.0, 1.0)[:, 0]
    red = painted_picture[rows, columns, 0]
    tiny = painted.texels(np.array([[[0.5, 0.5], [0.5004, 0.5], [0.5, 0.5004]]]), (size, size))[0]
    sage = np.column_stack([np.linspace(0.4, 0.5, 20), np.full(20, 0.5), np.full(20, 0.45)])
    like = painted.kind_like(np.vstack([sage, [[0.1, 0.05, 0.05]]]))
    return [bool(count and np.abs(red - wanted).max() < 1e-6), bool(np.ptp(red) > 0.02), bool(len(tiny)),
            bool(like[:-1].all() and not like[-1])]


def hood_kept(open_front=False):
    """A body 1 high whose neck (4 cm radius) rises out of a high collar (a ring 10 to 12 cm out) above a cut at 0.80,
    the hood kept from 0.85 down (`head_swap.kept_region`; `open_front`, a hoodie's): which of the head's faces under
    the hood's depth it keeps (the throat in front, the chin's underside in front turned down, the collar's front at
    10 cm, the collar's side at 10 cm, the neck's side turned out, the neck's side turned in, a bearded chin's front
    8.5 cm out)."""
    angles = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    heights = np.linspace(0.80, 0.82, 5)
    neck = [(0.04 * np.sin(angle), -0.04 * np.cos(angle), height) for angle in angles for height in heights]
    collar = [(radius * np.sin(angle), -radius * np.cos(angle), height) for angle in angles for height in heights
              for radius in (0.10, 0.12)]
    kept = head_swap.kept_region(0.80, 1.0, 1.0, (0.0, 0.0), 0.15, np.array(neck + collar), open_front)
    point = types.SimpleNamespace
    faces = [(point(x=0.0, y=-0.04, z=0.81), point(x=0.0, y=-1.0, z=0.0)),
             (point(x=0.0, y=-0.03, z=0.84), point(x=0.0, y=0.0, z=-1.0)),
             (point(x=0.05, y=-0.087, z=0.81), point(x=0.0, y=-1.0, z=0.0)),
             (point(x=-0.1, y=0.0, z=0.81), point(x=-1.0, y=0.0, z=0.0)),
             (point(x=-0.04, y=0.0, z=0.81), point(x=-1.0, y=0.0, z=0.0)),
             (point(x=-0.04, y=0.0, z=0.81), point(x=1.0, y=0.0, z=0.0)),
             (point(x=0.0, y=-0.085, z=0.83), point(x=0.0, y=-1.0, z=0.0))]
    return [bool(kept(centre, normal)) for centre, normal in faces]


def seam_order():
    """A head path that runs 3 cm and doubles back 1 cm, 6 mm further on, laid along a straight body path 2 mm in front
    of its first leg (`head_swap.laid_path`): (whether the points' nearest body points keep the head's order, whether
    the laid targets do, the targets' largest distance off the body path in mm)."""
    head_line = np.vstack([np.column_stack([np.linspace(0.0, 0.03, 31), np.zeros(31), np.zeros(31)]),
                           np.column_stack([np.linspace(0.029, 0.02, 10), np.full(10, -0.006), np.zeros(10)])])
    body_line = np.array([[0.0, -0.002, 0.0], [0.04, -0.002, 0.0]])
    lengths = head_swap.along(body_line)
    nearest, _ = head_swap.on_polyline(head_line, body_line, lengths)
    targets, laid = head_swap.laid_path(head_line, body_line, 0.003, 0.012)
    placed, off = head_swap.on_polyline(targets[laid], body_line, lengths)
    return [bool((np.diff(nearest) >= -1e-12).all()), bool((np.diff(placed) >= -1e-12).all()),
            round(float(off.max()) * 1000, 6)]


def seam_loop():
    """A neck's cut just under the jaw: the body's edge a closed loop 5 cm round (its ends 3 mm apart, opened at the
    back), the head's a loop 5.3 cm round run the other way and opened at the side (`head_swap.laid_path`, closing at
    1 cm): (the head's share laid, whether every target lies within 0.5 mm of the body's loop, whether they run once
    round)."""
    body_angles = np.linspace(0.0, 2.0 * np.pi - 0.06, 120)
    body_line = np.column_stack([0.05 * np.sin(body_angles), 0.05 * np.cos(body_angles), np.zeros(120)])
    head_angles = np.pi / 2.0 - np.linspace(0.0, 2.0 * np.pi, 140)
    head_line = np.column_stack([0.053 * np.sin(head_angles), 0.053 * np.cos(head_angles), np.zeros(140)])
    targets, laid = head_swap.laid_path(head_line, body_line, 0.003, 0.012, 0.01)
    radius = np.linalg.norm(targets[laid, :2], axis=1)
    turn = np.unwrap(np.arctan2(targets[laid, 0], targets[laid, 1]))
    return [round(float(laid.mean()), 2), bool(np.abs(radius - 0.05).max() < 0.0005),
            bool(abs(abs(turn[-1] - turn[0]) - 2.0 * np.pi) < 0.2)]


def seam_band():
    """A head's band, two walls 3 mm apart (the outer facing out, the inner in, joined at the sides) with a ragged
    edge (every other edge point 1.5 mm off), laid onto a body cut edge 2 to 5 mm in front of it
    (`head_swap.seam_shifts`, a body 1 high): (new folds, the outer edge's share laid at least 0.9, its laid points'
    largest distance off the body's edge under a micrometre)."""
    columns, rows, level, band = 61, 14, 0.0, head_swap.BAND
    across = np.linspace(-0.03, 0.03, columns)
    heights = np.linspace(level, level + band * 1.3, rows)
    walls = []
    for depth, facing in ((0.0, -1.0), (0.003, 1.0)):
        grid = np.zeros((rows, columns, 3))
        grid[..., 0] = across[None]
        grid[..., 1] = -0.010 + depth + 0.002 * np.sin(60 * across)[None]
        grid[0, 1::2, 1] += 0.0015
        grid[..., 2] = heights[:, None]
        walls.append((grid.reshape(-1, 3), facing))
    points = np.vstack([wall for wall, _ in walls])
    normals = np.vstack([np.tile([0.0, facing, 0.0], (rows * columns, 1)) for _, facing in walls])
    triangles = []
    for wall in range(2):
        start = wall * rows * columns
        for row in range(rows - 1):
            for column in range(columns - 1):
                corner = start + row * columns + column
                triangles += [[corner, corner + 1, corner + columns], [corner + 1, corner + columns + 1, corner + columns]]
    for side in (0, columns - 1):  # the walls joined at the sides
        for row in range(rows - 1):
            outer, inner = row * columns + side, rows * columns + row * columns + side
            triangles += [[outer, inner, outer + columns], [inner, inner + columns, outer + columns]]
    body_x = np.linspace(-0.035, 0.035, 71)
    body = np.column_stack([body_x, -0.0135 + 0.0015 * np.sin(60 * body_x + 0.5), np.zeros(71)])
    segments = (body[:-1], body[1:], np.tile([0.0, -1.0, 0.0], (70, 1)))
    moved, _, new = head_swap.seam_shifts(points, np.array(triangles), normals, level, band, (0.0, 0.02), segments,
                                          1.0, head_swap.SNAP_REACH)
    edge = np.arange(columns)
    shifted = np.linalg.norm(moved[edge] - points[edge], axis=1) > 1e-9
    _, off = head_swap.on_polyline(moved[edge][shifted], body, head_swap.along(body))
    return [new, bool(shifted.mean() >= 0.9), bool(off.max() < 1e-6)]


def chin_read():
    """A face's middle column over the cut: the throat 1 cm forward up to 2 cm, the chin and face 5 cm forward above,
    a shoulder 9 cm forward off the column (`head_swap.chin_over_cut`): (the chin's height, a column with no chin
    refused)."""
    heights = np.linspace(0.0, 0.07, 141)
    forward = np.where(heights < 0.02, 0.01, 0.05)
    shoulder = (np.full(20, 0.005), np.full(20, 0.09), np.full(20, 0.05))
    chin = head_swap.chin_over_cut(np.r_[heights, shoulder[0]], np.r_[forward, shoulder[1]],
                                   np.r_[np.zeros(141), shoulder[2]])
    try:
        head_swap.chin_over_cut(heights, np.full(141, 0.01), np.zeros(141))
    except ValueError:
        return [round(chin, 4), "refused"]
    return [round(chin, 4), "read"]


def chin_profile(chin_depth):
    """A face's middle column in Blender's frame (z up, the face toward -y), body 1 high with its crown at 1: the nose
    8 cm forward at 0.07 under the crown, the face 6 cm forward down to `chin_depth`, the throat 3 cm forward under it."""
    depths = np.linspace(0.0, 0.24, 481)
    forward = np.where(depths < chin_depth, np.where(np.abs(depths - 0.07) < 0.01, 0.08, 0.06), 0.03)
    return np.c_[np.zeros(len(depths)), -forward, 1.0 - depths]


def chin_cut():
    """The cut read off the swapped head (`head_swap.chin_under_crown`, `chin_whole`): [the chin's bottom under the
    crown, its front; a cut there kept, the hood's chin kept the head's, the hood's collar front the body's; a face 2 cm
    off the body's axis: its chin's front read on its own column through the nose, its chin under the hood kept the
    head's; a column with no chin refused; a cut that took the chin refused]."""
    points = chin_profile(0.142)
    chin = head_swap.chin_of(points, (0.0, 0.0), 1.0, 1.0)
    level = 1.0 - chin[0] - head_swap.CUT_UNDER_CHIN
    whole = head_swap.chin_whole(points[points[:, 2] > level], (0.0, 0.0), 1.0, 1.0, chin, level)
    kept = head_swap.kept_region(level, 1.0, 1.0, (0.0, 0.0), 0.125, np.zeros((0, 3)),
                                   chin=(1.0 - chin[0], chin[1]))
    point = types.SimpleNamespace
    held = [kept(point(x=0.0, y=-0.06, z=0.87), point(x=0.0, y=-1.0, z=0.0)),
            kept(point(x=0.05, y=-0.087, z=0.86), point(x=0.0, y=-1.0, z=0.0))]
    found = [round(chin[0], 4), round(chin[1], 3), round(whole[0], 4), *held]
    side = chin_profile(0.142)  # a face 2 cm off the axis, the chin's side 4.5 cm forward on the axis
    side[:, 1] = np.where(side[:, 2] > 1.0 - 0.142, -0.045, -0.015)
    off = np.r_[chin_profile(0.142) + [0.02, 0.0, 0.0], side]
    off_chin = head_swap.chin_of(off, (0.0, 0.0), 1.0, 1.0)
    reach = head_swap.face_reach(off, (0.0, 0.0), 1.0, 1.0, (0.125, off_chin[0]))
    off_kept = head_swap.kept_region(level, 1.0, 1.0, (0.0, 0.0), 0.125, np.zeros((0, 3)),
                                     chin=(1.0 - off_chin[0], reach))
    found += [round(off_chin[1], 3), off_kept(point(x=0.02, y=-0.06, z=0.87), point(x=0.0, y=-1.0, z=0.0))]
    for cut in (lambda: head_swap.chin_of(chin_profile(0.3), (0.0, 0.0), 1.0, 1.0),
                lambda: head_swap.chin_whole(points[points[:, 2] < 0.87], (0.0, 0.0), 1.0, 1.0, chin, level)):
        try:
            cut()
            found.append("read")
        except (ValueError, SystemExit):
            found.append("refused")
    return found


def jaw_corner_kept():
    """Under a hood from 0.125 down over a chin 6 cm forward (`head_swap.kept_region`, JAW_BAND): which faces 55 degrees
    off the front 5.5 cm out the head keeps (5 mm under the hood's depth, 1.5 cm under it, the body's 5 mm under it,
    the head's 7.5 cm out past the face's reach 5 mm under it)."""
    chin = head_swap.chin_of(chin_profile(0.142), (0.0, 0.0), 1.0, 1.0)
    level = 1.0 - chin[0] - head_swap.CUT_UNDER_CHIN
    kept = head_swap.kept_region(level, 1.0, 1.0, (0.0, 0.0), 0.125, np.zeros((0, 3)), chin=(1.0 - chin[0], chin[1]))
    way = np.array([np.sin(np.radians(55.0)), -np.cos(np.radians(55.0))])
    point = types.SimpleNamespace
    out = point(x=way[0], y=way[1], z=0.0)
    return [bool(kept(point(x=radius * way[0], y=radius * way[1], z=height), normal))
            for radius, height, normal in ((0.055, 0.870, out), (0.055, 0.860, out), (0.055, 0.870, None),
                                           (0.075, 0.870, out))]


def person_framed():
    """A body (a box with a nose) thinned to a third, moved by a known similarity (scale 1.7, a 6 degree turn, a shift) and given half a
    millimetre of noise, framed again from a start 5% off in scale and 3 cm off in place (`person.framed`): (scale
    within 0.5%, every point within 2 mm)."""
    rng = np.random.default_rng(5)
    nose = trimesh.creation.icosphere(2, 0.05)
    nose.apply_translation((0.06, 0.3, 0.1))
    shape = trimesh.util.concatenate([trimesh.creation.box((0.3, 1.0, 0.2)), nose])
    source = trimesh.sample.sample_surface(shape, 6000, seed=5)[0]
    rotation = turned(6.0, [0.0, 1.0, 0.0])
    target = 1.7 * source[::3] @ rotation.T + (0.02, 0.9, -0.01) + rng.normal(scale=5e-4, size=(2000, 3))
    scale, found, shift, _ = person.framed(source, target, (1.7 * 1.05, np.eye(3), np.array((0.05, 0.9, 0.0))))
    off = np.linalg.norm(scale * source @ found.T + shift - (1.7 * source @ rotation.T + (0.02, 0.9, -0.01)), axis=1)
    return [bool(abs(scale / 1.7 - 1.0) < 0.005), bool(off.max() < 0.002)]


def tether_inside_read():
    """A box body's points round it: (outside points the planes push past 1 mm, inside points they leave past 1 mm
    in, inside points), each read off the box's NEIGHBOURS nearest points' planes."""
    box = trimesh.creation.box((0.2, 0.4, 0.1)).subdivide().subdivide().subdivide()
    points = np.random.default_rng(0).uniform([-0.15, -0.25, -0.08], [0.15, 0.25, 0.08], (3000, 3))
    truth = trimesh.proximity.signed_distance(box, points)
    corners = np.asarray(box.vertices)
    over, normals = cloth_tether.outside(points, corners, cloth_tether.vertex_normals(corners, np.asarray(box.faces)))
    pushed = points + np.maximum(0.0, 0.002 - over)[:, None] * normals
    after = trimesh.proximity.signed_distance(box, pushed)
    moved = np.linalg.norm(pushed - points, axis=1)
    return [int(((truth < -0.003) & (moved > 0.001)).sum()), int(((truth > 0.001) & (after > 0.001)).sum()),
            int((truth > 0.001).sum())]


def neck_toned():
    """The body's neck under the cut toned to the head's skin: [its pink paint (L 61, a 20, b 19, spread 4) moved onto
    the photo's skin (L 76, a 13, b 16, spread 10) lands within 0.5 of its median, its spread not widened; the move's
    share 2 cm over the cut (over the paint's band), half way up the band, at the cut, 11 cm and 14 cm under it, 18 cm
    under it; the hoodie man's neck, a white scarf, a black collar, the stairwell woman's neck read as skin; the
    head's stubble share 0.4 carried 5 cm and 18 cm down; the seam's colour whole on the head and none past its
    fade]."""
    rng = np.random.default_rng(3)
    paint = np.array([61.0, 20.0, 19.0]) + rng.normal(0.0, 4.0, (2000, 3))
    photo = np.array([76.0, 13.0, 16.0]) + rng.normal(0.0, 10.0, (2000, 3))
    move = head_swap.neck_move(paint, photo)
    moved = head_swap.lab_of(head_swap.moved_srgb(head_swap.srgb_of(paint), move))
    band = head_swap.PAINT_BAND
    seam = head_swap.seam_offsets(np.full((2, 3), 0.6), np.full((2, 3), 0.8),
                                  np.array([0.0, head_swap.SEAM_FADE_M]))
    return [bool(np.abs(np.median(moved, 0) - np.median(photo, 0)).max() < 0.5),
            bool(np.all(np.std(moved, 0) <= np.std(paint, 0) * 1.05)),
            head_swap.neck_share([0.02, band / 2, 0.0, -0.06, -0.08, -0.1]).round(2).tolist(),
            head_swap.skin_like(np.array([[60.8, 20.0, 19.2], [87.0, 3.0, 8.0], [10.0, 0.5, 0.5],
                                          [67.1, 13.5, 23.5]])).tolist(),
            head_swap.stubble_carried(np.zeros(2), np.array([-0.03, -0.1]), np.full(2, 0.4)).round(2).tolist(),
            [bool(np.all(seam[0] < -0.1)), bool(np.all(seam[1] == 0.0))]]


def plate_cast(origins, ways, reaches):
    """The first meeting of each ray with a plate z = 0.2 x over |x|, |y| < 0.1 wound face down."""
    normal = np.array([0.2, 0.0, -1.0]) / np.sqrt(1.04)
    rise = ways[:, 2] - 0.2 * ways[:, 0]
    along = -(origins[:, 2] - 0.2 * origins[:, 0]) / np.where(np.abs(rise) > 1e-12, rise, 1e-12)
    location = origins + ways * along[:, None]
    hit = (along >= 0.0) & (along <= reaches) & (np.abs(location[:, :2]) < 0.1).all(axis=1)
    return hit, location, np.tile(normal, (len(origins), 1))


def hair_over_plate():
    """[strands moved, every point over the plate at least CLEAR_M over it, every step 5 cm still, a strand slid off
    the plate's low edge, the strand beside the plate unchanged]."""
    heights = np.linspace(0.125, -0.125, 6)
    strands = np.array([[[x, 0.0, z] for z in heights] for x in (-0.05, -0.025, 0.0, 0.025, 0.05, 0.3)])
    grid = np.stack(np.meshgrid(np.linspace(-0.1, 0.1, 41), np.linspace(-0.1, 0.1, 41)), -1).reshape(-1, 2)
    points = np.c_[grid, 0.2 * grid[:, 0]]
    size = over_cloth.voxel_size(np.linalg.norm(np.diff(strands, axis=1), axis=2), [0.005])
    laid, moved = over_cloth.laid_over(strands, plate_cast, over_cloth.cloth_keys(points, np.zeros((0, 3), int), size),
                                       size)
    over = (np.abs(laid[..., :2]) < 0.1).all(axis=-1)
    height = (laid[..., 2] - 0.2 * laid[..., 0]) / np.sqrt(1.04)
    steps = np.linalg.norm(np.diff(laid, axis=1), axis=2)
    return [moved, bool(height[over].min() >= over_cloth.CLEAR_M - 1e-9), bool(np.allclose(steps, 0.05)),
            bool((laid[0, -1, 0] < -0.09) & (laid[0, -1, 2] < -0.05)), bool(np.array_equal(laid[-1], strands[-1]))]


@pytest.mark.parametrize("case, made_value, wanted", [
    ("each painted pupil is found on the face", pupils_found, [True, True]),
    ("the eyeball sits behind its lid margins, its cornea just behind their rim", behind_lids, [True, True]),
    ("the painted floor inside the ball is removed, nothing outside the opening is", floor_removed, [True, True]),
    ("the floor beside the ball is pushed straight back into the socket's shade, the lids stay", floor_pushed_lids_kept,
     [True, True, True, True]),
    ("the wet line runs on the lids' inner rims round both eyes", wet_line_on_rims, [True, True, True]),
    ("both eyes gaze at one point straight ahead", gaze_agrees, True),
    ("a brown iris is read off the photo", lambda: iris_read((0.36, 0.2, 0.12)), True),
    ("a grey-blue iris is read off the photo", lambda: iris_read((0.4, 0.47, 0.52)), True),
    ("a lid margin is read steep or gentle, past a bump on the floor, and never on a curved floor", margins_read,
     [6, 9, 8, None]),
    ("an eye with no lid over or under it is refused", lidless_refused, "refused"),
    ("the hair's labels cover the painted top and nothing else", lambda: bool(labels_hold()[0]), True),
    ("the scalp closes the hair's hole under its shell, flush with the skin", lambda: bool(scalp_closes()[0]), True),
    ("the strands root on the scalp, stay out of the head and reach into the shell",
     lambda: bool(strands_fill()[0]), True),
    ("the hair's skin is laid onto the scalp at the hole's edge, no lip standing", lambda: skin_laid() < 0.002, True),
    ("a strand's layer runs from the scalp's side to the shell's outer surface", shell_layers, (True, True)),
    ("the shell's grooves and paint streaks are read as its flow", groove_and_streak, (True, True)),
    ("the photo's straight hair reads straight, its waves their size", photo_waves, (True, True)),
    ("the roots fade in over the hairline, none on the chin, the beard fades down the neck", roots_and_beard_fade,
     (True, True, True)),
    ("the neck's back under a bob meets the scalp's foot behind it", neck_meets_nape, -0.0792),
    ("the neck closes the hole the hair left in the jaw's corner at the skin's height", neck_closes_jaw, 1.0),
    ("the neck runs all round under the jaw's skin, whichever side the swap gives the head", neck_under_jaw, 1.0),
    ("the scalp meets the jaw's corner standing out under the ear, never an ear", scalp_holds_jaw, (True, True)),
    ("a darker hair gets more melanin, a warm one its hue's redness, a grey head the white share, melanin and redness "
     "whose swatch shows its colour and spread", lambda: bool(fibre_fitted()[0]), True),
    ("the photo's hair holds a silver bob as light as its backdrop and little else",
     lambda: (lambda found: (found[0] > 0.9, found[1] < 0.05))(silver_hair_read()), (True, True)),
    ("a hair-white bit on the forehead the clothes' colour claims is hair, the dark brows there never",
     white_bits_kept_as_hair, (1, 1.0, 0.0)),
    ("under a fringe no roots on the forehead under the hairline table, beside it and over it the paint's; with no "
     "fringe the paint's", forehead_roots,
     ((0.0, 1.0, 1.0), (1.0, 1.0, 1.0))),
    ("a swapped head's similarity is found exactly, a turn never a mirror",
     lambda: (similarity_found()[0] < 1e-9, similarity_found()[1]), (True, 1.0)),
    ("a swapped head's two-way ICP lands within a millimetre", lambda: icp_found() < 1e-3, True),
    ("the head's scale is read between the scan's steps", scale_scanned, 0.257),
    ("the seam's weight is all body at the cut, none at the band's top", seam_weights, [1.0, 0.5, 0.0]),
    ("a UV triangle's texels are those inside it", lambda: (0.5 <= texel_share()[0] < 0.56, texel_share()[1]),
     (True, True)),
    ("the head-to-body matrix moves a glTF point as Blender's moves it", lambda: frames_agree() < 1e-12, True),
    ("the close-up photo is registered onto the model's front from a start off by pixels and scale",
     lambda: skin_registered()[0], True),
    ("the photo's shading and gloss are taken off, plain skin kept", skin_light_off, [True, True, True]),
    ("plain skin between a brow and the lashes is no highlight, a cheek's highlight still is", skin_matte_beside_brows,
     [True, True]),
    ("a socket the photo shades deeper than the fit is lifted to the open skin, a stain on open skin kept dark",
     skin_socket_shade_off, [True, True]),
    ("under the hood's depth the head keeps its neck alone, its own collar front and side given to the body",
     hood_kept, [True, True, False, False, True, False, False]),
    ("the garment under the jacket may show round the neck (a hood) off the arms, not behind the chest",
     cloth_shirt_round_neck, [True, False, False, True]),
    ("the jeans' points ride no arm, a point a laid hand shares keeps its hand weights",
     cloth_jeans_off_arms, [0.0, 0.5, 1.0, 0.0]),
    ("a jacket piece wholly round the neck inside the hood is the hood's, a collar reaching down stays the jacket's",
     cloth_hood_inside, ["shirt", "jacket"]),
    ("an arm's face under the jacket's hem before a thigh is the trousers, a hand held out beside it is not",
     cloth_fused_to_leg, [True, False, False]),
    ("a beard grows as dense as its style reads off the close-up", beard_density_read, 0.5),
    ("a face no kind's place allows takes the nearest paint's kind, never the head", cloth_nowhere_kind,
     ["jeans", "jeans", "jeans"]),
    ("the beard takes a pale chin joined to the lips, never the lips", beard_chin_under_lip, [False, True, False]),
    ("under a hood open in front (a hoodie's) the head keeps its whole front, chin and beard, down to the cut",
     lambda: hood_kept(open_front=True), [True, True, True, False, True, False, True]),
    ("still_rig's fan across the cut's loop, one out over it and a collar's whole are found, the neck and an "
     "armpit's fan are kept", neck_fans_found, [48, 0, 0, 1, 26]),
    ("the Head's share on the neck under the cut moves down the neck chain by height, eased out over the cut",
     neck_off_the_head, [[0.6, 0.4, 0.0, 0.0], [0.0, 0.583, 0.167, 0.25], [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0],
                         [1.0, 0.0, 0.0, 0.0]]),
    ("the head's open edge at the cut is hung with a skirt down and in, facing out", head_edge_skirted,
     [48, -0.013, 0.045, 1.0]),
    ("the neck reads the photo's skin over the lower face, the skirt lands on the body's neck within reach, the "
     "neck is cut level", skirt_landed_neck_level, [[True, False, False, False], 12, True, True, True]),
    ("the body's own collar over the cut is released, the head's neck and the body under not; the hair read on it",
     neck_roles_read, [True, False, False, True, False]),
    ("the body's own faces round the neck take their kind by paint, its old hair and the rest stay the head",
     cloth_neck_released, ["jacket", "head", "skin", "head", "jacket"]),
    ("the body's old hair round the neck is painted over as the kind it lies on, its own points weighted as it",
     old_hair_painted_over, (["jacket", "skin", "head"], [False, True, False, True, False], 0)),
    ("the old hair's own texels wear the garment's paint at their nearest points, sage only, however small",
     old_hair_repainted, [True, True, True, True]),
    ("a hollow the model shuts reads shut, the photo's darker, warmer light in it divided out", skin_hollow_light_off,
     [True, True]),
    ("the photo's fringe and lid openings are kept off, its brows and moustache kept; the model's painted fringe "
     "wears no photo, its beard's middle may; the share rises from its outer edge", skin_photo_kept_off, [True] * 6),
    ("a bearded man's photo beard joins his face, the hood's folds and the backdrop never, a shaded cheek is no beard; "
     "his model's painted cheeks are no head hair", skin_photo_beard_worn, [True] * 5),
    ("a point wears the photo only facing forward, on the front, in the photo's face, clear of the eye; the T-zone "
     "holds the nose", skin_shares, [True] * 7),
    ("the photo's iris is unrolled onto the eyeball: its pupil's share read, the catchlight gone, the white outside",
     iris_unrolled, [True, True, True]),
    ("the paint's dark baked shade is lifted to the skin round it, plain skin and hair left",
     paint_lifted, [True, True, True]),
    ("a painted brow wearing the photo is skin, one not wearing it keeps its own material", skin_wears_photo,
     [True, True]),
    ("a point on a steep side is on the front, one behind it is not", steep_point_seen, [True, False]),
    ("the paint on the skin gets the photo skin's colour and spread, the hair keeps its paint", paint_toned,
     [True, True, True]),
    ("a hidden layer never comes through the lid the move pulls forward", layers_kept, [True, True, True]),
    ("the lids' triangles split in four and closed round them with no crack", split_closed, [True, True, True]),
    ("the photo's opening is read round each eye and held inside the ball", photo_opening, [True] * 4),
    ("the lids moved onto the photo's opening, thin over the eye and never inside it", lids_reshaped,
     [True, True, True]),
    ("upper lashes rise from the margin, lower ones fall, all leaving forward", lashes_grown, [True] * 6),
    ("a photo with dense lashes gets the full lashes, one with a few gets fewer", lashes_by_photo, [True, True]),
    ("the brow's hairs grow where the photo's brow is dark, lying on the skin", brows_follow_photo, [True, True]),
    ("the painted brow is painted over with the skin round it", brow_painted_over, [True, True]),
    ("a garment's kinds follow the paint: a fleck or stray faces join the piece round them", cloth_kinds_settled, 0),
    ("the jeans ride the skin a waistband's width under their top, measured over the cloth", cloth_waistband,
     [True, True]),
    ("a walk's repeated last frame is dropped and its travel carried on cycle after cycle", cloth_walk_tiled,
     [4, 0.3, 1, 0.6]),
    ("the body under the clothes is pushed in to the margin under a close shell, never under a far one",
     cloth_body_pushed, [round(cloth.MARGIN_M - 0.005, 3), 0.0]),
    ("a garment's sim mesh is laid over the body onto its inner wall: one piece, its two ends its only rims, manifold, "
     "the sliver and the speck gone", cloth_tube_laid, [2, 1, 2, True]),
    ("a remeshed needle is collapsed and a bow tie split into two fans", cloth_mesh_mended,
     [True, True, 6, [0, 1, 2, 3, 4, 5]]),
    ("the drawn surface rides its sim mesh exactly at rest and rigidly when it moves; a piece hung by nothing rides "
     "whole; its own normals turn with its skinning", cloth_drawn_rides, [True, True, 1, True, True, True]),
    ("a face hanging from a leg is jacket only above a long coat's hem, never a hand's under its wrist",
     cloth_jacket_off_legs, [[True, False, False], [True, True, False, False]]),
    ("a laid hand's wrist painted like the jacket is skin, the sleeve stays jacket", cloth_laid_hands_skin,
     [True, True]),
    ("a long coat's hem is read from the outside, under the trousers it hangs over", cloth_hem_found, [0.6, True]),
    ("a scarf standing forward of the shirt in the open front is its own garment; one depth is no scarf",
     cloth_scarf_split, [True, True, True]),
    ("a long coat under the hip joints hangs from both thighs and the pelvis as a skirt; its cuff, its top and a "
     "short jacket keep their own; a hand on it eases it in", cloth_skirted,
     [0.6, True, [0.0, 0.0, 1.0], True, True, True, True, 0.135]),
    ("a garment's seam to a skinned kind takes none of the cloth's move, eased in over SEAM_EASE_M", seam_held_to_shoe,
     [0.0, 0.33, 1.0]),
    ("the jeans' weights are smoothed over their own surface, their seams to other kinds kept",
     jeans_weights_smoothed, [True, True, True]),
    ("a jeans hem resting on a shoe takes the foot's weights, the leg above keeps the shin's", hem_turns_with_shoe,
     [0.667, 0.0, True]),
    ("a remeshed edge under a third of the mesh's edge is collapsed", cloth_short_edge_collapsed, [True, True]),
    ("a face's paint is read at its own row of the picture, glTF's v running down", cloth_paint_read_from_top, True),
    ("the body under the clothes wears the person's own shirt and trousers", cloth_under_coloured, [True, True, True]),
    ("the paint is toned toward the photo garment by garment: the jacket's sage, the boots' brown under trousers "
     "painted as black, the folds kept", colour_toned, [True] * 4),
    ("the body is never toned: hair and a face painted half skin, half dark keep their paint, the jacket is toned",
     colour_body_kept, [True] * 4),
    ("a swapped model's head and body pictures are each toned through their own UVs and kept at their own size",
     colour_two_parts, [[(128, 64), (256, 128)], [True, True]]),
    ("tethered cloth: riding points on their targets, every point within its tether, never deeper than its target, "
     "the loose cloth swinging, the edges held", tether_curtain, [True] * 5),
    ("tethered cloth feels only the gravity its turn adds to its rest hang", tether_gravity, [0.0, 13.87, 19.62]),
    ("a point is inside the body only where all its nearest body points' planes say so",
     lambda: (lambda found: (found[0] <= 5, found[1] <= 0.03 * found[2]))(tether_inside_read()), (True, True)),
    ("the hair step's removed triangles are read back from the faces it kept", person_hair_removed, [1, 7, 8, 30]),
    ("head.glb wears the skin step's sRGB paint as it is, never encoded again",
     lambda: np.asarray(head.paint_picture(np.full((2, 2, 3), 0.5)))[0, 0].tolist(), [128, 128, 128]),
    ("a body thinned and stood by a turn, a scale and a shift is framed again onto the rig", person_framed,
     [True, True]),
    ("the chin is the lowest slice standing forward of the throat, a shoulder off the face's column never",
     chin_read, [0.02, "refused"]),
    ("the cut lies under the chin read off the swapped head, never through it", chin_cut,
     [0.1425, 0.06, 0.1425, True, False, 0.06, True, "refused", "refused"]),
    ("under a hood's depth the jaw's corner within the face's reach stays the head's, the body keeping its own",
     jaw_corner_kept, [True, False, False, False]),
    ("a head path that doubles back is laid along the body path in order, on the path", seam_order, [False, True, 0.0]),
    ("a ragged two-walled band is laid onto the body's cut edge with no fold", seam_band, [0, True, True]),
    ("a head loop under the jaw is laid all round the body's closed loop", seam_loop, [1.0, True, True]),
    ("a scarf rides from where it meets anything over the chest, a turtleneck's collar too",
     cloth_scarf_rides_round_neck, [True, True]),
    ("the body's neck under the cut takes the photo's skin the head wears, whole under the cut, eased out, its "
     "blotches never widened, the head's stubble carried down, a scarf never skin", neck_toned,
     [True, True, [0.0, 0.5, 1.0, 1.0, 0.5, 0.0], [True, False, False, True], [0.4, 0.0], [True, True]]),
    ("strands hanging through a garment lie on and over it on their roots' side, their steps kept, the rest untouched",
     hair_over_plate, [5, True, True, True, True]),
])
def test_a_generated_head_gets_real_eyes_and_regrown_hair(case, made_value, wanted):
    assert made_value() == wanted, case
