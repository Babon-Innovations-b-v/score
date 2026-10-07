"""The picture's own detail laid over a generated piece's library surfaces (hub round four, 2026-10-07; numpy only, so
it runs inside Blender and in its check alike).

Round three kept only which library material each region of a piece is and threw the picture's colour away, and with
it everything the old pieces carried in colour: labels, taped notes, stickers, number plates, rust, worn paint and the
tools' own colours (the detail-loss diagnosis). Two ways were weighed to bring them back:

    decals         crops of the picture (cut by SAM 2.1 in the cloud) laid as Godot Decal nodes at the picture's spots
    masked blend   the picture, projected onto the piece by the model's own camera, baked into the piece's own texture
                   and blended over the library surface wherever it differs from that surface

The masked blend is the robust one: it needs no cut-out model, no placing step and no per-detail data, so it cannot
drop or float a detail; it carries what lies on curved and small parts (a tool's red grip, a rusty radio case) that a
flat decal cannot; and it costs nothing in the game (decals share Forward+'s clustered elements with the lights).

Per texel of the piece: `body` is the picture's usual colour for that library region facing that way (the median over
every texel of the same material slot and the same facing, so the studio light's side shading drops out). Where the
picture differs from its body by more than DETAIL_LOW (CIE76 in Lab) it takes over, fully past DETAIL_HIGH: that is a
label, a note, rust, a tool. Everywhere else the library colour stays, its lightness moved by the picture's own
lightness against the body (within WEAR_RANGE): scratches, grime and wood grain in the library's hue.

Two things in the picture are never detail (the coordinator, after stage one's renders): shade, a wide grey patch
darker than its body, which left dark blotches on the comms desk; and anything where the picture's camera never looked,
where Pixal3D guessed and drew streaks down the locker's side. Thin dark lines (print, gaps, scratches) stay.
"""
import numpy as np

DETAIL_LOW = 12.0
DETAIL_HIGH = 24.0
WEAR_RANGE = (0.7, 1.25)
# Shade (shade_blobs): darker than its body by DARK_STEP (L*), greyer than NEUTRAL_CHROMA, wider than 2 x BLOB_RADIUS
# texels; it darkens the library by no more than SHADE_WEAR.
DARK_STEP = 6.0
NEUTRAL_CHROMA = 12.0
BLOB_RADIUS = 4
SHADE_WEAR = 0.9
# Where the picture's camera never looked: lightness within this, no detail.
UNSEEN_WEAR = (0.92, 1.08)
# ... and the normal map's relief there is cut to this share (bake.Atlas.calm_unseen).
UNSEEN_RELIEF = 0.3
# Laid detail is paper, paint, rust or plastic: no metal, at least this rough.
DETAIL_ROUGHNESS = 0.75
# A group (slot and facing) with fewer covered texels than this takes its slot's body instead.
FEWEST = 400
FACINGS = 6


def linear(srgb):
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def encoded(lin):
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0.0, None), 1 / 2.4) - 0.055)


def lab(srgb):
    """sRGB (0..1, last axis) to CIE Lab."""
    xyz = linear(srgb) @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz = xyz / np.array([0.9505, 1.0, 1.089])
    bent = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * bent[..., 1] - 16, 500 * (bent[..., 0] - bent[..., 1]), 200 * (bent[..., 1] - bent[..., 2])],
                    -1)


def facing_of(normals):
    """Each texel's facing (0..5: +x, -x, +y, -y, +z, -z) from its object-space normal."""
    axis = np.abs(normals).argmax(-1)
    negative = np.take_along_axis(normals, axis[..., None], -1)[..., 0] < 0
    return axis * 2 + negative


def bodies(picture, groups, covered):
    """Per texel, its group's median picture colour; a sparse group takes its slot's (groups // FACINGS)."""
    found = np.zeros_like(picture)
    slots = groups // FACINGS
    for slot in np.unique(slots[covered]):
        in_slot = covered & (slots == slot)
        slot_body = np.median(picture[in_slot], axis=0)
        for group in np.unique(groups[in_slot]):
            members = in_slot & (groups == group)
            found[members] = np.median(picture[members], axis=0) if members.sum() >= FEWEST else slot_body
    return found


def smoothstep(low, high, value):
    share = np.clip((value - low) / (high - low), 0.0, 1.0)
    return share * share * (3 - 2 * share)


def softened(field):
    """A 3 x 3 mean, so a lone texel's speckle neither starts nor breaks a detail."""
    padded = np.pad(field, 1, mode="edge")
    return sum(padded[1 + down:padded.shape[0] - 1 + down, 1 + across:padded.shape[1] - 1 + across]
               for down in (-1, 0, 1) for across in (-1, 0, 1)) / 9.0


def windowed(mask, radius, combine):
    """A mask combined over a square window of `radius` texels each way (np.logical_and: shrunk, np.logical_or:
    grown), the outside counting as empty."""
    found = mask.copy()
    for axis in (0, 1):
        padded = np.pad(found, [(radius, radius) if index == axis else (0, 0) for index in (0, 1)],
                        constant_values=False)
        size = found.shape[axis]
        found = combine.reduce([np.take(padded, range(shift, shift + size), axis=axis)
                                for shift in range(2 * radius + 1)])
    return found


def eroded(mask, radius):
    return windowed(mask, radius, np.logical_and)


def dilated(mask, radius):
    return windowed(mask, radius, np.logical_or)


def shade_blobs(picture, body):
    """Where the picture is darker than its body and grey (no colour of its own), in patches wider than 2 x
    BLOB_RADIUS: the studio light's shade and Pixal3D's dark guesses, never a thing on the piece. Thin dark lines
    (print, stencils, scratches, panel gaps) are narrower and are kept as detail."""
    picture_lab, body_lab = lab(picture), lab(body)
    grey = np.linalg.norm(picture_lab[..., 1:], axis=-1) < NEUTRAL_CHROMA
    dark = (picture_lab[..., 0] < body_lab[..., 0] - DARK_STEP) & grey
    return dilated(eroded(dark, BLOB_RADIUS), BLOB_RADIUS)


def laid(library_colour, roughness, metal, picture, slots, normals, covered, seen):
    """The library surface with the picture's detail over it, where `covered` (the piece's own texels).

    library_colour, picture: (h, w, 3) sRGB 0..1; roughness, metal: (h, w); slots: (h, w) material slot index;
    normals: (h, w, 3) object-space normals; covered, seen: (h, w) bool, `seen` where the picture's camera looked.
    Shade (shade_blobs) is never detail and darkens the library by SHADE_WEAR at most; where the camera never looked
    there is no detail at all and the lightness moves within UNSEEN_WEAR only (Pixal3D's guesses there drew comb-like
    streaks down the locker's side, 2026-10-07). Returns colour, roughness, metal and the share of covered texels the
    picture's detail took over."""
    groups = slots * FACINGS + facing_of(normals)
    body = bodies(picture, groups, covered)
    difference = softened(np.linalg.norm(lab(picture) - lab(body), axis=-1))
    shade = shade_blobs(picture, body)
    detail = smoothstep(DETAIL_LOW, DETAIL_HIGH, difference) * covered * seen * ~shade
    weights = np.array([0.2126, 0.7152, 0.0722])
    lightness = (linear(picture) @ weights) / np.maximum(linear(body) @ weights, 1e-4)
    lower = np.where(seen, np.where(shade, SHADE_WEAR, WEAR_RANGE[0]), UNSEEN_WEAR[0])
    upper = np.where(seen, WEAR_RANGE[1], UNSEEN_WEAR[1])
    worn = encoded(linear(library_colour) * np.clip(lightness, lower, upper)[..., None])
    worn = np.where(covered[..., None], worn, library_colour)
    colour = worn + (picture - worn) * detail[..., None]
    rough = roughness + (np.maximum(roughness, DETAIL_ROUGHNESS) - roughness) * detail
    shine = metal * (1.0 - detail)
    share = float(detail[covered].mean()) if covered.any() else 0.0
    return np.clip(colour, 0.0, 1.0), rough, shine, share
