"""The finish route's parts row, `surfaces-parts` (free, on this PC's processor): the method's interface (PARTS in
__init__.py) written from the route's split, so the framework's rows (paint, bake, check) and every reader of the
parts (the likeness, the machines) take it as they took the finish-map method's.

Its finishes are the list's. Each finish's surface is checked against its colour in the close-up before the bake,
free (finish_parts.checked_finishes, the same check the finish-map method ran; the paper's "a finish's surface must
lie within dE 32 of its colour there"): its colour is read where the close-up shows it (`close_up_colours`: the
model cast through the close-up's own camera, each pixel taking the finish of the face under it), never the raw
model's texture, whose colours carry the picture's baked light. A take with no own close-up or camera, or whose cast
does not fit the close-up's outline (route_cast.CLOSE_UP_FIT, or its outline lies within COLOUR_OFFSET of the
close-up's: `outline_offset`), is measured on its views' texture instead
(`seen_colours`), named so in its record (`colour_from`), as a stand-in close-up is. A finish off its listed surface
takes the nearest surface of its family that fits, or one of the scene's own shell surfaces
(palette_library.shell_surfaces: the variants its surface library gives the shell laid from its locked plan); one no surface fits is marked off its colour with a
proposed surface, and the paint's gate "colour against the close-up" fails it by name. The bake check holds each
baked part against the same close-up colour (bake_check.close_up_faults, its `measured_lab`). Each part takes its finish's
checked surface (finish_parts.part_rows), and the list's settings where its finish kept the surface the list named
(route_settings.applied: the bake paints and bakes the surface with them). A light built in code (`lit_take`: a
light bar, strip or string the thin straight route built, score/stages/props/thin_straight.py) is its light: every
lit finish (`lit_finishes`) takes the scene library's glowing surface (the library's `glowing` recipe) nearest the
colour its concept crop shows (`lit_finishes`; owner, 2026-10-25: "the engines themself should be a source of light and there are lights in
the concept"); with none in the scene library it is marked off its colour, and the paint's gate names it.

Output: parts.json (per take its method, parts (each with its finish's `settings` or None and its own `wear`
{level, cause} or None), finishes with the list's settings and the check's measure, `decals` (each listed mark
placed: its library decal, part, point, facing, up and size in the take's own frame, cast through the close-up's
camera, score #164) and `decal_gaps`; the takes left out and why), <take>/parts.npy (one part per face of the raw take,
the paint's face order), <take>/colours.npy (NaN: the paint joins parts on their surface alone), <take>/texels.npz
(the split's, carried: one part per texel of the model's pictures). Gate "parts": every
take the split split has its parts.
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_parts  # noqa: E402
import palette_library  # noqa: E402
import route_cast as cast  # noqa: E402
import route_data  # noqa: E402
import route_settings  # noqa: E402
import route_split  # noqa: E402
import surface_gates as gates  # noqa: E402
import text_decals  # noqa: E402
import score.stages.batch_gaps as batch_gaps  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402
import score.stages.props.thin_straight as thin_straight  # noqa: E402

METHOD = "finish-route"
# A finish's colour is read off the close-up through a cast under CLOSE_UP_FIT too when the cast's outline lies on
# average within COLOUR_OFFSET of the close-up's (outline_offset, in the cast's pixels): a thin frame's long outline
# holds its IoU low while its inner pixels (EDGE) still lie on their finish. tc4r (#186): the rack at IoU 0.82 lay 2.7
# px off and read its beams salmon (L*a*b* 51.5 19.2 12.4) where its views' texture read them saturated red (49.7 56.8
# 37.8, the list's #b83030 beams, NVIDIA's albedo dE 43 to 50 from it); the surgical chair at 0.715 lay 6.2 px off and
# read its black plastic white (L* 99.7). The thirteen others fit at 0.877 to 0.995.
COLOUR_OFFSET = 3.0
EDGE = 2  # a pixel counts when those EDGE away on every side show its finish too, so no border mixes two finishes
# A printed mark is placed by casting its box through the close-up's camera (score #164): its middle gives its part,
# point and facing, and a probe EDGE_IN of the box inside each edge its size and up, so a probe sits on the mark, not
# beside it; a probe on another part (or off the model) is not used, and a mark both of whose sizes miss its part is a
# gap, so a decal never reaches past its part.
EDGE_IN = 0.1
# A route's own print under a text or line mark is looked for in the mark's box grown by this share of its shorter side
# each way: TRELLIS.2's garbled "03" on the tc2 sign lay round the close-up's digits, not on them (#171).
COVER_GROW = 0.25
# A drawn mark is sized by its own ink cast on its part (ink_extent): at most INK_MOST pixels, at least INK_FEWEST, a
# word's span between quantiles INK_TRIM from each end, a line's band in RULE_BIN metre bins.
INK_MOST, INK_FEWEST, INK_TRIM, RULE_BIN = 6000, 20, 0.01, 0.002
LETTER_SHARE = 0.3  # a piece of a text mark's ink is a letter when at least this share of its tallest's height
LETTER_WIDEST = 3.0  # and at most this many times as wide as it is tall (a line's end in the box is not a letter)
PROBES = {"middle": (0.5, 0.5), "left": (EDGE_IN, 0.5), "right": (1 - EDGE_IN, 0.5), "top": (0.5, EDGE_IN),
          "bottom": (0.5, 1 - EDGE_IN)}


def seen_colours(views, finish_of, count):
    """Each finish's median CIELAB colour over the pixels of its faces in every view of the model's texture, or None
    where no view shows it."""
    faces = dict(np.load(views / "faces.npz"))
    colours = dict(np.load(views / "colours.npz"))
    found = []
    for number in range(count):
        pixels = np.concatenate([colours[view][(faces[view] >= 0) & (finish_of[np.maximum(faces[view], 0)] == number)]
                                 for view in faces])
        found.append(np.median(cast.lab_of(pixels), axis=0) if len(pixels) else None)
    return found


def inner(finish_map):
    """The pixels whose neighbours EDGE away on every side show the same finish (-1: none)."""
    kept = finish_map >= 0
    for axis in (0, 1):
        for shift in (EDGE, -EDGE):
            kept &= np.roll(finish_map, shift, axis=axis) == finish_map
    return kept


def outline_offset(shown, hit):
    """How far, on average, the cast's outline (`hit`) lies from the close-up's (`shown`), in pixels: the pixels only
    one of them covers over the mean of their outlines' lengths."""
    from scipy import ndimage
    def outline(mask):
        return int((mask & ~ndimage.binary_erosion(mask)).sum())
    return float((shown ^ hit).sum() / max((outline(shown) + outline(hit)) / 2, 1))


def colours_read(fit, offset):
    """Whether a cast through the close-up's camera reads each finish's colour: it fits the close-up's outline
    (CLOSE_UP_FIT) or lies near it (COLOUR_OFFSET)."""
    return fit >= cast.CLOSE_UP_FIT or offset <= COLOUR_OFFSET


def close_up_colours(model, camera_file, close_up, finish_of, count):
    """(each finish's median CIELAB colour in the close-up where it shows it (inner pixels the cast and the close-up's
    alpha share), None where it shows none; the cast's fit: its outline's IoU with the close-up's; its outline_offset)."""
    faces, sampled, both, fit = cast.close_up_pixels(model, camera_file, close_up)
    finish_map = np.where(both, finish_of[np.maximum(faces, 0)], -1)
    kept = inner(finish_map)
    found = []
    for number in range(count):
        pixels = sampled[kept & (finish_map == number)][:, :3]
        found.append(np.median(cast.lab_of(pixels), axis=0) if len(pixels) else None)
    return found, fit, round(outline_offset(sampled[..., 3] > 127, faces >= 0), 2)


def finish_colours(folders, finish_of, count):
    """(each finish's colour, where it was read): the close-up's (close_up_colours) when the take has its own
    close-up and camera and the cast fits it (CLOSE_UP_FIT) or lies near its outline (COLOUR_OFFSET), else its views'
    texture (seen_colours), with why."""
    if folders.get("close_up") and folders.get("camera"):
        found, fit, offset = close_up_colours(cast.loaded(folders["model"]), folders["camera"], folders["close_up"],
                                              finish_of, count)
        if colours_read(fit, offset):
            return found, f"close-up (outline fit {fit}, {offset} px off)"
        why = (f"views: the close-up's cast fits its outline at IoU {fit}, under {cast.CLOSE_UP_FIT}, {offset} px off, "
               f"over {COLOUR_OFFSET}")
    else:
        why = "views: no own close-up or camera"
    return seen_colours(folders["views"], finish_of, count), why


def part_finish(mesh, part_of, finish_of, part):
    """The finish a part takes, as finish_parts.part_rows chose it: the finish over most of its area."""
    members = part_of == part
    return int(np.bincount(finish_of[members], weights=mesh.area_faces[members]).argmax())


def mark_probes(box):
    """The close-up pixels a mark's box is cast at ([column, row] for each of PROBES, in its order)."""
    left, top, wide, tall = box
    return [[left + across * wide, top + down * tall] for across, down in PROBES.values()]


def spanned(points, on_part, first, second, inner):
    """The distance between two probes on the mark's part, grown from the probes to the box's edges, or None."""
    if not (on_part[first] and on_part[second]):
        return None
    return float(np.linalg.norm(points[second] - points[first])) / inner


def square_up(up, normal):
    """`up` made square to `normal` and of length 1, or None when it lies along it."""
    up = np.asarray(up, dtype=float) - float(np.dot(up, normal)) * normal
    length = float(np.linalg.norm(up))
    return None if length < 1e-6 else up / length


def placement(mark, number, faces, points, part_of, normals, seen):
    """One mark's placement ({decal, part, at, normal, up, size, turn, layer, ink_token, what, from}) in the take's own
    frame, or the reason it cannot be placed: its middle off the model, or both its sizes off its part."""
    names = list(PROBES)
    middle = faces[names.index("middle")]
    if middle < 0:
        return None, "its box's middle is off the model"
    part = int(part_of[middle])
    on_part = {name: faces[at] >= 0 and part_of[faces[at]] == part for at, name in enumerate(names)}
    points = dict(zip(names, np.asarray(points, dtype=float)))
    inner = 1 - 2 * EDGE_IN
    wide = spanned(points, on_part, "left", "right", inner)
    tall = spanned(points, on_part, "top", "bottom", inner)
    if wide is None and tall is None:
        return None, f"it spans more than its part {part}"
    ratio = mark["box"][2] / max(mark["box"][3], 1)
    wide, tall = (wide if wide is not None else tall * ratio), (tall if tall is not None else wide / ratio)
    normal = np.asarray(normals[middle], dtype=float)
    seen_up = points["top"] - points["bottom"] if on_part["top"] and on_part["bottom"] else np.array([0.0, 1.0, 0.0])
    up = square_up(seen_up, normal)
    for fallback in ([0.0, 1.0, 0.0], [0.0, 0.0, 1.0]):  # seen edge-on: the take's up, else its front
        up = square_up(fallback, normal) if up is None else up
    rounded = lambda vector: [round(float(value), 5) for value in vector]  # noqa: E731
    drawn = {"shape": mark["shape"], "text": mark.get("text"), "look": mark.get("look"),
             "font": text_decals.FONTS.get(mark.get("look"))} if mark.get("shape") in text_decals.DRAWN else {}
    return {"decal": mark["decal"], "part": part, "at": rounded(points["middle"]), "normal": rounded(normal),
            "up": rounded(up), "size": [round(wide, 5), round(tall, 5)], "turn": 0.0, "layer": number,
            "ink_token": mark.get("ink_token"), "what": mark.get("what", ""), **drawn,
            "from": {"close_up_box": mark["box"], "seen": seen}}, None


def decal_placements(marks, part_of, normals, cast, seen):
    """(placements, gaps) of a take's listed marks (route_list's, finish_ask.marks_of): each mark naming a library
    decal, and each text or line mark (text_decals.DRAWN, drawn in a library face), cast through the close-up
    (`cast(pixels)` -> (faces, points in the take's own frame), route_cast.cast_points) and placed on the part under
    its middle (placement); a mark with a gap, or with no decal and not drawn, or that cannot be placed, a gap naming
    why. `seen` says which close-up the boxes are in."""
    placements, gaps = [], []
    for number, mark in enumerate(marks):
        if mark.get("gap") or (mark.get("decal") is None and mark.get("shape") not in text_decals.DRAWN):
            gaps.append({"what": mark.get("what", ""), "why": mark.get("gap") or "no library decal named"})
            continue
        faces, points = cast(mark_probes(mark["box"]))
        found, why = placement(mark, number, faces, points, part_of, normals, seen)
        if found is None:
            gaps.append({"what": mark.get("what", ""), "decal": mark["decal"], "why": why})
        else:
            placements.append(found)
    return placements, gaps


def close_up_seen(folders):
    """(the model, its close-up's camera, the close-up's size, None) when the take has its own close-up and camera and
    the camera's cast fits the close-up's outline (route_cast.CLOSE_UP_FIT), else (None, None, None, why not)."""
    if not (folders.get("close_up") and folders.get("camera") and folders.get("model")):
        return None, None, None, f"no own close-up and camera ({route_data.STAND_IN}): its box cannot be cast"
    from PIL import Image
    model = cast.loaded(folders["model"])
    fit = cast.close_up_pixels(model, folders["camera"], folders["close_up"])[3]
    if fit < cast.CLOSE_UP_FIT:
        return None, None, None, f"the close-up's cast fits its outline at IoU {fit}, under {cast.CLOSE_UP_FIT}"
    with Image.open(folders["close_up"]) as picture:
        size = picture.size
    return model, cast.close_up_camera(folders["camera"]), size, None


def ink_pixels(box, picture, ink, text=True):
    """[[column, row], ...] of a drawn mark's ink in the close-up (`picture` RGBA): the opaque pixels of its box
    nearer the ink's colour (`ink`, sRGB 0-255) than the box's median colour, at most INK_MOST of them, evenly. A text
    mark's are its letters: the pieces of ink at least LETTER_SHARE as tall as its tallest and at most LETTER_WIDEST
    times as wide as tall (the tc2 sign's "03" and "Patient room" boxes held ends of the line between them); all of
    its ink when no piece is."""
    left, top, wide, tall = (int(value) for value in box)
    crop = picture[top:top + tall, left:left + wide]
    shown = crop[..., 3] > 127
    if not shown.any():
        return np.zeros((0, 2))
    colours = crop[..., :3].astype(float)
    base = np.median(colours[shown], axis=0)
    inked = shown & (np.linalg.norm(colours - ink, axis=-1) < np.linalg.norm(colours - base, axis=-1))
    if text and inked.any():
        from scipy import ndimage
        pieces, _ = ndimage.label(inked)
        spans = np.array([[found[0].stop - found[0].start, found[1].stop - found[1].start]
                          for found in ndimage.find_objects(pieces)])
        letters = (spans[:, 0] >= LETTER_SHARE * spans[:, 0].max()) & (spans[:, 1] <= LETTER_WIDEST * spans[:, 0])
        inked = np.isin(pieces, 1 + np.flatnonzero(letters)) if letters.any() else inked
    rows, columns = np.nonzero(inked)
    every = max(1, len(rows) // INK_MOST)
    return np.c_[columns[::every] + left + 0.5, rows[::every] + top + 0.5]


def ink_extent(placement, points, normals):
    """The placement moved and sized to its ink (#171: the list's boxes run loose and, seen at an angle, an upright
    box holds a slanted line's height, the tc2 sign's printed line 285 px tall): `points` its ink cast on its part (the
    take's own frame), each across and up its face from its point; a text mark spans its ink between the INK_TRIM and
    1 - INK_TRIM quantiles each way, a line the band across its up where its ink is densest (RULE_BIN bins at least
    half the densest's count) and its ink's span along it. Its facing is its ink's faces' mean (`normals`, one a
    point): one face's under its middle tilts on a route's bumpy mesh, so a thin line's slab cut the face aslant. As it
    was with fewer than INK_FEWEST points."""
    if len(points) < INK_FEWEST:
        return placement
    normal = normals.mean(0) / np.linalg.norm(normals.mean(0))
    up = square_up(placement["up"], normal)
    up = square_up([0.0, 1.0, 0.0], normal) if up is None else up
    right = np.cross(up, normal)
    offset = points - placement["at"]
    across, upward = offset @ right, offset @ up
    if placement["shape"] == "rule":
        bins = np.floor(upward / RULE_BIN).astype(int)
        counts = np.bincount(bins - bins.min())
        dense = np.flatnonzero(counts >= counts.max() / 2) + bins.min()
        band = np.isin(bins, dense[np.abs(dense - (counts.argmax() + bins.min())) <= len(dense)])
        across, upward = across[band], upward[band]
        low, high = [across.min(), upward.min()], [across.max(), upward.max() + RULE_BIN]
    else:
        low, high = np.quantile(np.c_[across, upward], [INK_TRIM, 1 - INK_TRIM], axis=0)
    middle = (np.asarray(low) + np.asarray(high)) / 2
    at = np.asarray(placement["at"]) + middle[0] * right + middle[1] * up
    rounded = lambda vector: [round(float(value), 5) for value in vector]  # noqa: E731
    return dict(placement, at=rounded(at), normal=rounded(normal), up=rounded(up),
                size=[round(float(high[0] - low[0]), 5), round(float(high[1] - low[1]), 5)])


def drawn_print(mark):
    """True for a text or line mark drawn as a text decal over a print finish of the list's own (its `print_finish`)."""
    return not mark.get("gap") and mark.get("shape") in text_decals.DRAWN and mark.get("print_finish") is not None


def printed_finishes(finishes, marks):
    """The finishes, each a drawn mark prints (drawn_print) marked `printed`: its colour is the mark's ink, which the
    colour check takes as its own (finish_parts.checked_finishes)."""
    printed = {mark["print_finish"] for mark in marks if drawn_print(mark)}
    return [dict(finish, printed=True) if number in printed else finish for number, finish in enumerate(finishes)]


def covered_prints(seen, marks, finish_of, part_of):
    """The faces a route's own print shows under the text and line marks (#171: TRELLIS.2 garbles words into blots of
    the print's colour) given the finish and part the mark is printed on, in place: a face of the mark's print finish
    (finish_ask.marks_of's `print_finish`) seen in its box grown by COVER_GROW takes its `on_finish` and the part of
    that finish seen most there, the parts then numbered again with none left empty. `seen` is close_up_seen's; the
    faces moved."""
    model, camera, size, _ = seen
    faces, rows, columns = cast.close_up_cast(model, camera, size)
    moved = 0
    for mark in marks:
        if not drawn_print(mark):
            continue
        left, top, wide, tall = mark["box"]
        grow = COVER_GROW * min(wide, tall)
        inside = ((columns >= left - grow) & (columns <= left + wide + grow) & (rows >= top - grow)
                  & (rows <= top + tall + grow) & (faces >= 0))
        under = np.unique(faces[inside])
        base = under[finish_of[under] == mark["on_finish"]]
        printed = under[finish_of[under] == mark["print_finish"]]
        if not len(base) or not len(printed):
            continue
        finish_of[printed] = mark["on_finish"]
        part_of[printed] = np.bincount(part_of[faces[inside][np.isin(faces[inside], base)]]).argmax()
        moved += len(printed)
    part_of[:] = np.unique(part_of, return_inverse=True)[1]  # parts numbered from 0 with none emptied (part_rows)
    return moved


def inked(marks, close_up, inks):
    """(the marks, each text mark's box tightened to its letters' ink (ink_pixels), the listed one kept as
    `listed_box`; each drawn mark's ink pixels, None where its token is not the palette's ({token: "#rrggbb"}))."""
    from PIL import Image
    with Image.open(close_up) as opened:
        picture = np.asarray(opened.convert("RGBA"))
    found, pixels = [], []
    for mark in marks:
        token = (inks or {}).get(mark.get("ink_token"))
        if mark.get("gap") or mark.get("shape") not in text_decals.DRAWN or token is None:
            found.append(mark)
            pixels.append(None)
            continue
        ink = np.array([int(token.lstrip("#")[at:at + 2], 16) for at in (0, 2, 4)], dtype=float)
        seen = ink_pixels(mark["box"], picture, ink, mark["shape"] == "text")
        pixels.append(seen)
        if mark["shape"] == "text" and len(seen):
            low, high = np.floor(seen.min(0)), np.ceil(seen.max(0))
            mark = dict(mark, box=[int(low[0]), int(low[1]), int(high[0] - low[0]), int(high[1] - low[1])],
                        listed_box=mark["box"])
        found.append(mark)
    return found, pixels


def take_decals(seen, marks, part_of, out, inks=None, close_up=None):
    """(placements, gaps) of a take's marks: cast through its own close-up's camera (`seen`, close_up_seen), each text
    or line mark placed and sized by its ink in the `close_up` (inked, ink_extent; `inks` the palette's
    {token: "#rrggbb"}) and its picture drawn into `out` (text_decals.drawn, its placement's `picture` that file's name
    there); a take whose close-up cannot be cast places none, each mark a gap naming why."""
    if not marks:
        return [], []
    model, camera, size, why = seen
    if model is None:
        return [], [{"what": mark.get("what", ""), "decal": mark.get("decal"), "why": why} for mark in marks]
    marks, pixels = inked(marks, close_up, inks)
    placements, gaps = decal_placements(marks, part_of, model.mesh.face_normals,
                                        lambda pixels: cast.cast_points(model, camera, size, pixels), "close-up")
    for number, placement in enumerate(placements):
        if placement.get("shape") not in text_decals.DRAWN:
            continue
        ink = pixels[placement["layer"]]
        if ink is not None and len(ink):
            faces, points = cast.cast_points(model, camera, size, ink)
            kept = (faces >= 0) & (part_of[np.maximum(faces, 0)] == placement["part"])
            placement = ink_extent(placement, points[kept], model.mesh.face_normals[faces[kept]])
        placements[number] = dict(placement, picture=f"text-{number:02d}.png")
        text_decals.drawn(placements[number]).save(out / placements[number]["picture"])
    return placements, gaps


def part_wear(rows, finishes, mesh, part_of, finish_of):
    """Each part row's own wear ({level, cause}: the list's for its finish, score #164) or None, the finish's
    falling back to the scene's."""
    for row in rows:
        finish = finishes[part_finish(mesh, part_of, finish_of, row["part"])]
        row["wear"] = ({"level": finish["wear_level"], "cause": finish.get("wear_cause")}
                       if finish.get("wear_level") else None)


def files(place):
    """route_data.parts_files and each code-built take's mark (thin_straight.MARK beside its close-up), named
    `code <take>`."""
    found = route_data.parts_files(place)
    for name in [name for name in found if name.startswith("close-up ")]:
        mark = pathlib.Path(found[name]).parent / thin_straight.MARK
        if mark.is_file():
            found[f"code {name.removeprefix('close-up ')}"] = str(mark)
    return found


def lit_take(entry, mark):
    """Whether a code-built take (its `mark`, thin_straight's code.json) is a light's body: its kind glows
    (thin_straight.slender_light, by the row's noun and name the take carries) and it is no stem lamp (lamps.on_stem
    on its built size: a stem lamp's post is a post, its head the library's lamp)."""
    with prop_data.tools("props/scene"):
        import lamps
    built = json.loads(pathlib.Path(mark).read_text())
    return thin_straight.slender_light({"noun": entry.get("kind"), "name": entry.get("object")}) \
        and not lamps.on_stem({"size": built.get("size")})


def lit_finishes(checked, every):
    """A code-built light's checked finishes, each lit one given the glowing surface of `every` (one made with the
    library's `glowing` recipe) nearest its measured colour, else the first; each marked off its colour when `every`
    has none. Its lit finishes are those of a lit family (finish_parts.SEEN_THROUGH_FAMILIES, the list's family: the
    likeness row leaves the same ones to the light layer), and every finish when none is: a light bar's metal end caps
    keep their own surface once its build carries its crop and the split gives them their part (2026-10-29: airlock's
    wall lamp, its caps baked glowing), and a light listed as one body is its light."""
    glowing = sorted(name for name, spec in every.items() if spec.get("recipe") == "glowing" and "colour" in spec)
    lit = [finish.get("family") in finish_parts.SEEN_THROUGH_FAMILIES for finish in checked]
    found = []
    for finish, glows in zip(checked, lit if any(lit) else [True] * len(checked)):
        if not glows:
            found.append(finish)
            continue
        if not glowing:
            found.append(dict(finish, by="off its colour", fits=False, new_surface={
                "name": f"{finish['finish']} (glowing)", "description": f"{finish['finish']}, a light built in code",
                "why": "the scene library has no glowing surface for a light built in code",
                "lab": finish.get("measured_lab")}))
            continue
        colour = finish.get("measured_lab")
        nearest = min(glowing, key=lambda name: float(np.linalg.norm(finish_parts.library_lab(every[name]) - colour))
                      ) if colour is not None else glowing[0]
        found.append({**{key: value for key, value in finish.items() if key != "new_surface"},
                      "surface": nearest, "fits": True, "by": "its light, built in code"})
    return found


def parts_take(folders, entry, finishes, surfaces, marks=(), inks=None):
    """One take's parts into folders["out"]: parts.npy and colours.npy; its parts.json record, with each part's own
    wear (part_wear) and its listed marks placed as decals (take_decals). `surfaces`: the take's library surfaces
    (palette_library.take_surfaces) and the scene's shell surfaces (palette_library.shell_surfaces); `inks` the
    palette's tokens, a drawn mark sized by its ink (take_decals)."""
    finish_of = np.load(folders["split"] / "finish.npy").astype(int)
    part_of = np.load(folders["split"] / "parts.npy").astype(int)
    mesh = route_split.model_of(folders["views"])
    every, kit = surfaces
    colours, colour_from = finish_colours(folders, finish_of, len(finishes))
    checked = finish_parts.checked_finishes(entry, printed_finishes(finishes, marks), colours, every, kit)
    if folders.get("code") and lit_take(entry, folders["code"]):
        checked = lit_finishes(checked, every)
    checked = finish_parts.looked(checked, every)
    seen = close_up_seen(folders) if marks else (None, None, None, None)
    covered = covered_prints(seen, marks, finish_of, part_of) if seen[0] is not None else 0
    folders["out"].mkdir(parents=True)
    np.save(folders["out"] / "parts.npy", part_of.astype(np.int32))
    np.save(folders["out"] / "colours.npy", np.full((len(mesh.faces), 3), np.nan, dtype=np.float32))
    if (folders["split"] / "texels.npz").exists():
        shutil.copyfile(folders["split"] / "texels.npz", folders["out"] / "texels.npz")
    rows = finish_parts.part_rows(mesh, part_of, finish_of, checked)
    for row in rows:
        row["settings"] = route_settings.applied(checked[part_finish(mesh, part_of, finish_of, row["part"])])
    part_wear(rows, checked, mesh, part_of, finish_of)
    decals, decal_gaps = take_decals(seen, marks, part_of, folders["out"], inks, folders.get("close_up"))
    return {"method": METHOD, "object": entry.get("object"), "parts": rows, "judge_unknown": [], "finishes": checked,
            "colour_from": colour_from, "decals": decals, "decal_gaps": decal_gaps,
            "measures": {"parts": len(rows), "off colour": sum(entry["by"] == "off its colour" for entry in checked),
                         "decals": len(decals), "decal gaps": len(decal_gaps), "print faces covered": covered}}


def make_parts(inputs, out, seed, params):
    """Every split take's parts; parts.json, with the takes the split made gaps (or the list left out) as left
    out."""
    views, listed = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-list"])
    split = pathlib.Path(inputs["finish-route-split"])
    _, takes = route_data.takes_written(out, inputs, params)
    palette = palette_library.read(inputs)
    kit = palette_library.shell_surfaces(palette)
    split_takes = json.loads((split / "split.json").read_text())
    named = {take: entry["name"] for entry in batch_gaps.of(inputs) for take in entry["objects"]}
    found, left = {}, {}
    for take in takes:
        record = split_takes.get(take)
        if record is None or record["fault"]:
            left[take] = record["fault"] if record else named.get(take, "not split: no finish list")
            continue
        answer = json.loads((listed / f"{take}.json").read_text())
        finishes = answer["finishes"]
        folders = {"views": views / take, "split": split / take, "out": out / take, "model": inputs.get(f"model {take}"),
                   "close_up": inputs.get(f"close-up {take}"), "camera": inputs.get(f"camera {take}"),
                   "code": inputs.get(f"code {take}")}
        found[take] = parts_take(folders, takes[take], finishes, (palette_library.take_surfaces(takes[take], palette), kit),
                                 answer.get("marks", []), palette["tokens"])
    (out / "parts.json").write_text(json.dumps({"takes": found, "left_out": left}, indent=1))


def judge_parts(output, inputs, evidence):
    """Every take the split split has its parts; the takes left out (gaps named by the rows before) and the
    finishes off their colour as measures."""
    found = json.loads((output / "parts.json").read_text())
    split = json.loads((pathlib.Path(inputs["finish-route-split"]) / "split.json").read_text())
    failing = [f"{take}: no parts" for take, record in split.items()
               if not record["fault"] and take not in found["takes"]]
    return gates.verdict("parts", failing, len(found["takes"]) + len(found["left_out"]), "takes", {
        "left_out": len(found["left_out"]),
        "off colour": sum(record["measures"]["off colour"] for record in found["takes"].values())})


def judge_meaning(output, inputs, evidence):
    """Gate "kept the list's meaning": no finish the colour check moved off its listed surface lost the list's recipe
    (a glow kept a glow) or hue, and no take's largest finish so moved left the colour its row's name names
    (finish_parts.meaning_faults). The paint's colour gate and the bake check hold a surface to the close-up's lit
    colour, the same the re-pick matched, so a swap within dE 32 passed them by construction (the audit of
    2026-11-04)."""
    found = json.loads((output / "parts.json").read_text())["takes"]
    failing = [fault for take, record in found.items() for fault in finish_parts.meaning_faults(take, record)]
    moved = sum(finish["surface"] != finish.get("listed_surface", finish["surface"])
                for record in found.values() for finish in record["finishes"])
    return gates.verdict("kept the list's meaning", failing, len(found), "takes", {"moved": moved})
