"""Pattern decals (#210, PRD #159 round 12): a regular pattern of openings punched or moulded into a part (a locker
door's vent holes, a battery's cooling slots, a humidifier's ribs) is never a route's shape or texture: TRELLIS.2 draws
it as blobby bumps with black smears. The finish list reads it off the close-up as a mark of shape `pattern`
(finish_ask.marks_of: its opening, rows and columns, stagger, outline, the openings' width as a share of their
spacing, the way slots and ribs run, the token seen inside them); the parts row places it at its cast size as a decal
(route_parts.decal_placements, sized by its openings' ink) and draws it here from its library pattern (score_lib's
surfaces of family `pattern`, decal_library.patterns: the opening's shape, its length share, its relief and its
roughness), tiled at the mark's pitch inside its outline. It is printed as a one-ink decal (white through its
transparency, the bake printing it in its token's ink) and sunk by its pattern's relief (recipes.decal_layer's
`relief`), so the openings read dark and deep.

    density(placement)             the pixels a metre its picture is drawn at
    centres(placement)             each opening's middle across and up its box, in metres from its lower left
    drawn(placement)               the decal's picture (RGBA), its openings white through its transparency
"""
import numpy as np

SHAPE = "pattern"
SHAPES = ("disk", "stadium", "groove")  # the opening shapes a library pattern names (its `shape` tag)
OUTLINES = ("rectangle", "diamond", "circle")
ALONG = ("up", "across")  # the way a slot or a rib runs, in the close-up
PX_PER_M = 3000  # #161 rule 7: a part with print is baked at about 3,000 px a metre
OPENING_PX = 16  # the fewest pixels across an opening's narrow side (a drill battery's 2 mm slots are 6 px at 3,000)
MOST_PX = 4096
EDGE = 0.15  # the share of an opening's narrow half-width its rim slopes over, so its relief shades as a bevel
SLACK = 0.05  # an opening whose middle lies this share past its outline is still in it (a corner hole on the line)


def fills(placement):
    """(across, up): the share of its spacing an opening fills each way: its `opening_share` across a slot or a rib
    and both ways for a round hole; its pattern's `length_share` along a slot or a rib."""
    share, length = float(placement["opening_share"]), float(placement.get("length_share") or 1.0)
    if placement["opening_shape"] == "disk":
        return share, share
    return (share, length) if placement.get("along", "up") == "up" else (length, share)


def pitches(placement):
    """(across, up): the spacing between openings' middles in metres, its box (`size`) tight round its openings: the
    outer openings' far edges on its sides, so the box is (count - 1 + fill) spacings each way; a round hole's
    spacing up whatever leaves its rows, each a hole as wide as its spacing across gives, filling the box's height."""
    wide, tall = placement["size"]
    rows, columns = int(placement["rows"]), int(placement["columns"])
    fill_across, fill_up = fills(placement)
    across = wide / (columns - 1 + fill_across)
    if placement["opening_shape"] != "disk":
        return across, tall / (rows - 1 + fill_up)
    hole = min(fill_across * across, tall)
    return across, (tall - hole) / (rows - 1) if rows > 1 else tall


def opening_size(placement):
    """(across, up) of one opening in metres; a round hole as wide as tall, as its spacing across gives (at most the
    box's height)."""
    (fill_across, fill_up), (pitch_across, pitch_up) = fills(placement), pitches(placement)
    if placement["opening_shape"] == "disk":
        return (min(fill_across * pitch_across, placement["size"][1]),) * 2
    return fill_across * pitch_across, fill_up * pitch_up


def inside(across, up, outline):
    """Whether a middle at (across, up), each from -1 to 1 over the outer middles, lies in its outline."""
    if outline == "diamond":
        return abs(across) + abs(up) <= 1 + SLACK
    if outline == "circle":
        return across * across + up * up <= (1 + SLACK) ** 2
    return True


def centres(placement):
    """[[across, up], ...] each opening's middle in metres from its box's lower left: `rows` rows of `columns`, every
    second row (counting from the middle one) moved half a spacing across and one opening shorter when `staggered`,
    those whose middle lies outside its `outline` left out."""
    rows, columns = int(placement["rows"]), int(placement["columns"])
    (pitch_across, pitch_up), (size_across, size_up) = pitches(placement), opening_size(placement)
    wide, tall = placement["size"]
    half_across, half_up = max((wide - size_across) / 2, 1e-9), max((tall - size_up) / 2, 1e-9)
    found = []
    for row in range(rows):
        moved = bool(placement.get("staggered")) and (row - (rows - 1) // 2) % 2 == 1
        for column in range(columns - 1 if moved else columns):
            across = size_across / 2 + (column + (0.5 if moved else 0.0)) * pitch_across
            up = size_up / 2 + row * pitch_up
            if inside((across - wide / 2) / half_across, (up - tall / 2) / half_up, placement.get("outline")):
                found.append([across, up])
    return np.array(found).reshape(-1, 2)


def density(placement):
    """The pixels a metre its picture is drawn at: PX_PER_M, more where an opening's narrow side would be under
    OPENING_PX; its longer side at most MOST_PX."""
    narrow = max(min(opening_size(placement)), 1e-6)
    return min(max(PX_PER_M, OPENING_PX / narrow), MOST_PX / max(max(placement["size"]), 1e-6))


def opening(shape, wide, tall):
    """One opening's transparency (`wide` x `tall` px, 0 to 1): a disk, a stadium (a slot with round ends) or a groove
    (a straight cut across its whole length), its rim sloping over EDGE of its narrow half-width."""
    columns, rows = np.meshgrid(np.arange(wide) + 0.5 - wide / 2, np.arange(tall) + 0.5 - tall / 2)
    half = min(wide, tall) / 2
    if shape == "disk":
        distance = np.hypot(columns / (wide / 2), rows / (tall / 2)) * half
    elif shape == "stadium":
        reach = (max(wide, tall) / 2 - half)
        along, across = (columns, rows) if wide >= tall else (rows, columns)
        distance = np.hypot(np.maximum(np.abs(along) - reach, 0.0), across)
    else:
        distance = np.abs(rows if wide >= tall else columns)
    return np.clip((half - distance) / max(EDGE * half, 0.5), 0.0, 1.0)


def drawn(placement):
    """A pattern mark's picture (RGBA, white through its transparency) at its placement's size and density: each
    opening of its library shape (`opening_shape`) at its middle (centres)."""
    from PIL import Image
    scale = density(placement)
    wide, tall = (max(1, round(side * scale)) for side in placement["size"])
    alpha = np.zeros((tall, wide))
    size_across, size_up = (max(1, round(side * scale)) for side in opening_size(placement))
    shape = opening(placement["opening_shape"], size_across, size_up)
    for across, up in centres(placement):
        left, top = round(across * scale - size_across / 2), round((placement["size"][1] - up) * scale - size_up / 2)
        rows = slice(max(top, 0), min(top + size_up, tall))
        columns = slice(max(left, 0), min(left + size_across, wide))
        piece = shape[rows.start - top:rows.stop - top, columns.start - left:columns.stop - left]
        alpha[rows, columns] = np.maximum(alpha[rows, columns], piece)
    picture = np.zeros((tall, wide, 4), dtype=np.uint8)
    picture[..., :3] = 255
    picture[..., 3] = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(picture)
