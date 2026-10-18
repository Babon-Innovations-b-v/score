"""The picture of each materials finding, drawn from the place's linked assembly with PIL alone (no Blender):

    soft texture   a patch of PATCH metres of the room's kit beside one of the object, each texture pixel enlarged as
                   a block: the coarser the texture, the bigger its blocks
    ragged border  the model drawn flat-shaded along the view that faces its worst border, each finish its own colour
                   and its ragged borders in red: whole, and close round the worst run
    kit age        a patch of each stale kit piece's texture, with when it was baked and the bake code's commits since
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import cKDTree

from score.stages.complete.materials import borders, meshes

PATCH = 0.5
# Among how many of a model's largest painted triangles the most detailed patch is looked for.
CANDIDATES = 40
# From this many screen pixels a texture pixel, the patch shows a line between texture pixels.
GRID_CELL = 6
# A patch with more than this share of black pixels reaches into the atlas's empty space between its islands.
GAP = 0.1
# The shortest border run worth showing close (metres): a shorter one is a speck in the picture.
SHOWN_RUN = 0.2
SIDE = 420
CAPTION = 64
INK = (20, 20, 20)
PAPER = (245, 245, 242)
RED = (225, 30, 30)
FINISH_COLOURS = [(110, 150, 200), (220, 170, 90), (130, 190, 120), (190, 120, 180), (200, 200, 200), (120, 200, 200),
                  (160, 120, 90), (230, 120, 110)]


def font(size=16):
    """PIL's own font at a size."""
    return ImageFont.load_default(size=size)


def captioned(picture, lines):
    """The picture with lines of text under it."""
    out = Image.new("RGB", (picture.width, picture.height + CAPTION), PAPER)
    out.paste(picture, (0, 0))
    ImageDraw.Draw(out).multiline_text((8, picture.height + 6), "\n".join(lines), fill=INK, font=font(15))
    return out


def side_by_side(panels):
    """Pictures in one row on paper."""
    out = Image.new("RGB", (sum(panel.width for panel in panels) + 8 * (len(panels) + 1),
                            max(panel.height for panel in panels) + 16), PAPER)
    left = 8
    for panel in panels:
        out.paste(panel, (left, 8))
        left += panel.width + 8
    return out


# --- soft texture -------------------------------------------------------------------------------------------------

def painted_spots(drawn, count=CANDIDATES):
    """[(picture file, texture coordinate)] at the centres of the model's largest painted triangles."""
    found = []
    for mesh in drawn:
        if mesh.corners_uv is None:
            continue
        areas = meshes.triangle_areas(mesh.points, mesh.triangles)
        for name, faces in list(mesh.finishes.items()) + [("", np.arange(len(mesh.triangles)))]:
            picture = mesh.pictures.get(name)
            if picture and len(faces):
                found += [(areas[face], picture, mesh.corners_uv[face].mean(axis=0)) for face in faces]
    return [(picture, uv) for _, picture, uv in sorted(found, key=lambda item: -item[0])[:count]]


def texture_of(path):
    """A picture file as RGB."""
    with Image.open(path) as source:
        return source.convert("RGB")


def crop_at(texture, uv, side):
    """A square of `side` texture pixels round a texture coordinate."""
    centre_x, centre_y = (uv[0] % 1.0) * texture.width, (1.0 - uv[1] % 1.0) * texture.height
    half = side / 2
    return texture.crop((int(centre_x - half), int(centre_y - half), int(centre_x + half), int(centre_y + half)))


def busiest(drawn, side):
    """The crop of `side` texture pixels with the most detail (spread of brightness) among the largest painted
    triangles' centres, one that reaches into the atlas's empty black (GAP) only when every one does; or None."""
    textures, best = {}, None
    for picture, uv in painted_spots(drawn):
        texture = textures.setdefault(picture, texture_of(picture))
        crop = crop_at(texture, uv, side)
        values = np.asarray(crop, dtype=float)
        in_gap = float((values.max(axis=2) < 4).mean()) > GAP
        score = (not in_gap, float(values.mean(axis=2).std()))
        if best is None or score > best[0]:
            best = (score, crop)
    return best[1] if best else None


def gridded(picture, cells):
    """The picture with a faint line between its texture pixels where each is GRID_CELL screen pixels or more."""
    step = picture.width / cells
    if step < GRID_CELL:
        return picture
    draw = ImageDraw.Draw(picture)
    for number in range(1, cells):
        at = round(number * step)
        draw.line((at, 0, at, picture.height), fill=(255, 255, 255), width=1)
        draw.line((0, at, picture.width, at), fill=(255, 255, 255), width=1)
    return picture


def patch(drawn, px_per_m, metres=PATCH):
    """A square of `metres` of the model's surface as its texture holds it, each texture pixel enlarged as a block
    (gridded when large) to SIDE pixels: the coarser the texture, the bigger its blocks."""
    side = max(1, round(px_per_m * metres)) if px_per_m else 0
    crop = busiest(drawn, side) if side else None
    if crop is None:
        return Image.new("RGB", (SIDE, SIDE), (128, 128, 128))
    return gridded(crop.resize((SIDE, SIDE), Image.Resampling.NEAREST), side)


def soft_texture(finding, drawn, kit_model, kit_drawn, kit_density):
    """The kit's patch beside the object's, captioned."""
    kit = captioned(patch(kit_drawn, kit_density),
                    [f"kit: {kit_model}, {kit_density:.0f} px/m", f"{PATCH:.1f} m of its surface"])
    seen = captioned(patch(drawn, finding["px_per_m"]),
                     [f"{finding['model']}, {finding['px_per_m']:.0f} px/m", f"{PATCH:.1f} m of its surface, "
                      f"seen from {finding['near']:.1f} m"])
    return side_by_side([kit, seen])


# --- ragged border ------------------------------------------------------------------------------------------------

def gathered(drawn):
    """All the model's meshes as one: points, triangles, each triangle's finish number, the finish names."""
    points, triangles, labels, names = [], [], [], []
    offset = 0
    for mesh in drawn:
        merged, welded_triangles = borders.welded(mesh.points, mesh.triangles)
        mesh_labels, mesh_names = borders.face_labels(len(welded_triangles), mesh.finishes)
        numbers = [names.index(name) if name in names else names.append(name) or len(names) - 1 for name in mesh_names]
        labels.append(np.array([numbers[label] if label >= 0 else -1 for label in mesh_labels]))
        points.append(merged)
        triangles.append(welded_triangles + offset)
        offset += len(merged)
    return np.vstack(points), np.vstack(triangles), np.concatenate(labels), names


def keyed(picture, names):
    """The picture with a swatch and the name of each finish over its top left corner."""
    draw = ImageDraw.Draw(picture)
    for number, name in enumerate(names[:len(FINISH_COLOURS)]):
        top = 6 + 18 * number
        draw.rectangle((6, top, 20, top + 14), fill=FINISH_COLOURS[number], outline=INK)
        draw.text((26, top - 1), name, fill=INK, font=font(13))
    return picture


def worst_runs(drawn, parts):
    """The smooth border runs of the named parts, raggedest by length first, those of SHOWN_RUN or more when any is:
    [(ratio, points)]."""
    found = []
    for mesh in drawn:
        runs, _ = borders.part_runs(mesh)
        for name in parts:
            for line in runs.get(name, []):
                length, smoothed = borders.lengths(line)
                if smoothed > 0:
                    found.append((length / smoothed, length, line))
    long_enough = [item for item in found if item[1] >= SHOWN_RUN] or found
    return [(ratio, line) for ratio, _, line in sorted(long_enough, key=lambda item: -item[0] * item[1])]


def view_basis(normal):
    """Two axes across a view direction."""
    normal = normal / (np.linalg.norm(normal) or 1.0)
    helper = np.array([0.0, 1.0, 0.0]) if abs(normal[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    across = np.cross(helper, normal)
    across /= np.linalg.norm(across)
    return across, np.cross(normal, across), normal


def facing(points, triangles, line):
    """The area-weighted mean normal of the faces along a border run: the view that faces it."""
    steps = np.linalg.norm(np.diff(line, axis=0), axis=1)
    reach = 2 * float(np.median(steps)) if len(steps) else 0.01
    middles = points[triangles].mean(axis=1)
    distance, _ = cKDTree(line).query(middles)
    along = distance < reach
    if not along.any():
        return np.array([0.0, 0.0, 1.0])
    total = (borders.face_normals(points, triangles[along])
             * meshes.triangle_areas(points, triangles[along])[:, None]).sum(axis=0)
    return total if np.linalg.norm(total) > 1e-9 else np.array([0.0, 0.0, 1.0])


def drawn_panel(points, triangles, labels, view, centre, half, lines, nearest=None):
    """The model flat-shaded along `view` (across, up, toward the eye) in a window `half` metres round `centre`, the
    lines in red; faces nearer the eye than `nearest` metres in front of `centre` left out, so a border behind a
    fold shows."""
    across, up, toward = view
    scale = SIDE / (2 * half)
    flat = np.stack([(points - centre) @ across, (points - centre) @ up], axis=1) * scale
    flat[:, 1] *= -1
    flat += SIDE / 2
    depth = points[triangles].mean(axis=1) @ toward
    shade = np.abs(borders.face_normals(points, triangles) @ toward)
    picture = Image.new("RGB", (SIDE, SIDE), PAPER)
    draw = ImageDraw.Draw(picture)
    inside = np.any((flat[triangles] >= -SIDE * 0.1) & (flat[triangles] <= SIDE * 1.1), axis=(1, 2))
    if nearest is not None:
        inside &= depth <= float(centre @ toward) + nearest
    for face in np.nonzero(inside)[0][np.argsort(depth[inside])]:
        base = np.array(FINISH_COLOURS[labels[face] % len(FINISH_COLOURS)] if labels[face] >= 0 else (90, 90, 90))
        colour = tuple(int(value) for value in base * (0.35 + 0.65 * shade[face]))
        draw.polygon([tuple(corner) for corner in flat[triangles[face]]], fill=colour)
    for line in lines:
        shown = np.stack([(line - centre) @ across, -((line - centre) @ up)], axis=1) * scale + SIDE / 2
        draw.line([tuple(point) for point in shown], fill=RED, width=2)
    return picture


def ragged_border(finding, drawn):
    """The model whole and close round its worst border, captioned."""
    points, triangles, labels, names = gathered(drawn)
    runs = worst_runs(drawn, finding["parts"])
    if not runs:
        return None
    ratio, worst = runs[0]
    centre = worst.mean(axis=0)
    reach = float(np.linalg.norm(worst - centre, axis=1).max())
    view = view_basis(facing(points, triangles, worst))
    middle = (points.max(axis=0) + points.min(axis=0)) / 2
    whole_half = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0))) / 2
    close_half = min(max(reach * 1.2, 0.15), whole_half)
    lines = [line for _, line in runs]
    whole = drawn_panel(points, triangles, labels, view, middle, whole_half, lines)
    close = drawn_panel(points, triangles, labels, view, centre, close_half, [worst], nearest=max(reach, 0.05))
    return side_by_side([captioned(keyed(whole, names), [finding["model"]]),
                         captioned(close, [f"worst border {ratio:.2f} (clean 1.00)",
                                           f"window {2 * close_half:.2f} m across"])])


# --- kit age ------------------------------------------------------------------------------------------------------

def kit_age(finding, drawn_of, density_of, commits):
    """A patch of up to four stale pieces with their bake time, and the bake code's commits since."""
    panels = [captioned(patch(drawn_of[model], density_of.get(model)).resize((SIDE // 2, SIDE // 2)),
                        [model[:26]]) for model in finding["models"][:4]]
    row = side_by_side(panels)
    listed = [f"{commit['at'][:10]} {commit['commit']} {commit['subject'][:80]}" for commit in commits[:8]]
    text = Image.new("RGB", (max(row.width, 760), 30 + 20 * (len(listed) + 1)), PAPER)
    ImageDraw.Draw(text).multiline_text(
        (8, 8), "\n".join([f"{len(finding['models'])} kit pieces baked before these bake code commits:"] + listed),
        fill=INK, font=font(15))
    out = Image.new("RGB", (max(row.width, text.width), row.height + text.height), PAPER)
    out.paste(row, (0, 0))
    out.paste(text, (0, row.height))
    return out
