"""Branch B's finish (#168, PRD #159): TRELLIS.2's model taken through the library finish method, the surface stage's
finish route (score/stages/surfaces: views, list, split, parts), so every face of it lies in a finish group bound to a
library surface and the measures can hold its finish split against NVIDIA's face groups.

    library = bench_library(root)                     # the benchmark place's surface library (below)
    finished(model, close_up, row, library, folder)   # the route's rows run on one made model into `folder`
    face_finishes(folder, take)                       # (part a face, each part's surface) of a finished take
    part_looks(folder, take)                          # each part's look as its surface is set on it (#172)
    look_job(folder, take, model, camera, out)        # its look drawn by the texel masks, look.py's job (#182)
    marks_read(folder, ask=None)                      # each text mark of a drawn look read back (#185)
    surface_look(record)                              # a library surface's own look, from its recipe

**The benchmark place's surface library** is score_lib's surfaces in force as the finish route offers a scene's own
(palette_library's loader form, materials.json, with its palette.json): every adopted tiling surface at its fitted
recipe and settings, and the rest of score_lib's surfaces that carry a recipe (the recipes themselves, a scene's made
surfaces). A surface painted for one model (`painted_for`: its maps cover one model's UVs once) has no recipe and is
never offered, nor is one whose record names no recipe (`recipe_gap`); each such one is listed in `left_out`. The
benchmark's own models are never read here: only surfaces. A variant is named by its entry's id and keeps its address.
Its colour settings (colour, and bare and second where present) become palette tokens, their sRGB rounded to TOKEN_STEP
so near-equal colours share one (`token_of`); a recipe with no colour of its own (score_lib's recipe entries) stands in
NEUTRAL, which the list re-tokens. The palette holds every token, so the whole library is offered; its wear is `new`
and its dirt nothing (an NVIDIA asset is drawn clean).

**The route as it runs on a place** (score/stages/surfaces/CLAUDE.md): views (free), the list (finish-route-list's own
make, its ask sent to Claude as the place line sends it: claude_asks.asking_claude, EUR 0 on the subscription), split,
parts. The take's close-up is the benchmark's render cut out (`rgba.png`, TRELLIS.2's own input); TRELLIS.2 gives no camera
for it, so one is fitted from the model's outline against it (`fitted_camera`, score/stages/surfaces/close_up_fit.py,
#171) round the close-up style's view (place_build maker.close_up_view), and where its cast fits the close-up's outline
(route_cast.CLOSE_UP_FIT) the close-up is laid on the model, its colours read through it and its marks placed (text
and numbers drawn as text decals in a library face). The bake (make_chunky through a place's paint) is a place's and is not run here: the
measures read the parts, which name every face's surface.
"""
import json
import pathlib
import shlex
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[4]
SURFACES = REPO / "score/stages/surfaces"
for _folder in (SURFACES, REPO / "tools/props/library", REPO / "tools/library"):
    if str(_folder) not in sys.path:
        sys.path.append(str(_folder))

TOKEN_STEP = 8  # sRGB levels a token's colour is rounded to: near-equal colours share one token
NEUTRAL = "#808080"  # the default token of a recipe with no colour of its own
RECORD = "surface.json"
WEAR = {"level": "new", "dirt": 0.0}
SEED = 168
# The look's picture (look_job, look.py): its side and samples, #181's after pictures' (r3edges), a preview that
# never ships.
LOOK_SIDE, LOOK_SAMPLES = 1080, 32
# A text mark of the look is read (marks_read, #185) in its drawn box grown by this share of its longer side each way,
# so a garbled print beside the words is in the picture read too.
READ_MARGIN = 0.15
READ_GREY = 204  # the look's light grey world (look.py WORLD_GREY), behind the crop's clear pixels
READING = ("This picture is a close crop of a rendered object's surface where printed text should be. Read the printed "
           "text exactly as it appears, character by character, in reading order on one line. Leave out only print "
           "that the picture's edge cuts through (it belongs to a neighbouring mark). Write ? for every "
           "character that is not a clean, legible letter or digit (garbled, broken, blotched or partly missing). "
           "Never guess or complete a word from what it should say; when nothing legible is printed, answer an "
           "empty text.")


def token_of(linear):
    """A linear RGB colour's palette token: its sRGB hex rounded to TOKEN_STEP."""
    channels = [12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
                for value in np.clip(np.asarray(linear, dtype=float), 0.0, 1.0)]
    rounded = [min(255, int(round(value * 255 / TOKEN_STEP)) * TOKEN_STEP) for value in channels]
    return "#" + "".join(f"{value:02x}" for value in rounded)


def offered_addresses(root):
    """[(address, why left out or None)] of score_lib's surfaces in force: one painted for one model, or whose entry
    holds no surface record, left out by name."""
    from score import library
    found = []
    for row in library.index(root, "surface")["entries"]:
        if row.get("state") == "withdrawn":
            continue
        if row.get("tags", {}).get("painted_for"):
            found.append((row["address"], "painted for one model: its maps cover that model's UVs once"))
            continue
        kind, rest = row["address"].split("/", 1)
        entry_id, version = rest.split("@")
        path = pathlib.Path(root) / "entries" / kind / entry_id / version / "entry.json"
        files = json.loads(path.read_text())["files"] if path.is_file() else {}
        found.append((row["address"], None if RECORD in files else "its entry holds no surface.json"))
    return found


def records(addresses):
    """{address: its surface.json} through the library's files (library_files.resolve, hash-checked), every one not
    cached yet fetched first in one call of score_lib's own command into the library's file cache."""
    import library_files
    values = library_files.settings()
    missing = [address for address in addresses
               if not library_files.cache_folder().joinpath("score_lib", *address.replace("@", "/").split("/"),
                                                            RECORD).is_file()]
    if missing:
        words = shlex.split(values.get("SCORE_LIB_COMMAND") or library_files.DEFAULT_COMMAND) + [
            "--root", values["SCORE_LIB_ROOT"], "fetch", *missing, "--file", RECORD,
            "--into", str(library_files.cache_folder())]
        done = subprocess.run(words, env=library_files.blob_store(values), cwd=values["SCORE_LIB_ROOT"],
                              capture_output=True, text=True)
        if done.returncode:
            raise RuntimeError(f"score-lib fetch of {len(missing)} surface records exited {done.returncode}: "
                               f"{done.stderr.strip()[-400:]}")
    return {address: json.loads(library_files.resolve(library_files.reference(address, RECORD)).read_text())
            for address in addresses}


def variant_of(record):
    """(a surface record's variant in the loader's form, the tokens it names {token: hex}), or (None, why) for one with
    no recipe. An adopted surface's fitted settings are its own; a recipe entry's (`recipe` a name) its recipe's."""
    recipe = record.get("recipe")
    if isinstance(recipe, str):
        return {"recipe": recipe, "token": NEUTRAL}, {NEUTRAL: NEUTRAL}
    if not isinstance(recipe, dict) or not recipe.get("recipe"):
        return None, record.get("recipe_gap") or "its record names no recipe"
    settings = dict(recipe.get("settings") or {})
    tokens = {}
    colour = token_of(settings.pop("colour")) if "colour" in settings else NEUTRAL
    tokens[colour] = colour
    settings.pop("dirt_colour", None)
    for setting in ("bare", "second"):
        if setting in settings:
            settings[setting] = token_of(settings[setting])
            tokens[settings[setting]] = settings[setting]
    return {"recipe": recipe["recipe"], "token": colour, **settings}, tokens


def bench_library(root):
    """(materials.json content, palette.json content, addresses {variant: address}, left_out {address: why}): the
    benchmark place's surface library (module docstring). Each variant's family is its recipe."""
    method = json.loads((REPO / "data/library/materials.json").read_text())
    listed = offered_addresses(root)
    left = {address: why for address, why in listed if why}
    found = records([address for address, why in listed if not why])
    families, tokens, addresses = {}, {}, {}
    for address, record in sorted(found.items()):
        variant, named = variant_of(record)
        if variant is None:
            left[address] = named
            continue
        if variant["recipe"] not in method["recipes"]:
            left[address] = f"its recipe {variant['recipe']} is not one of the library's recipes"
            continue
        name = address.split("/", 1)[1].split("@")[0].lower()
        families.setdefault(variant["recipe"], {"surface": None, "variants": {}})["variants"][name] = variant
        tokens.update(named)
        addresses[name] = address
    dirt = min(tokens)
    library = {"is": "the prop benchmark's surface library: score_lib's surfaces in force (bench/run/finish.py)",
               "wear_levels": method["wear_levels"], "recipes": method["recipes"],
               "colour_settings": method.get("colour_settings", {}), "tokens": tokens, "dirt": dirt,
               "families": families, "kinds": {}, "pictures": {}}
    palette = {"tokens": tokens, "wear": {**WEAR, "dirt_token": dirt}}
    return library, palette, addresses, left


def library_written(library, folder):
    """The library's two row outputs in `folder`: surface-library/materials.json and finish-route-palette/palette.json,
    with addresses.json and left-out.json beside them; {row: its folder}."""
    content, palette, addresses, left = library
    rows = {"surface-library": folder / "surface-library", "finish-route-palette": folder / "finish-route-palette"}
    for path in rows.values():
        path.mkdir(parents=True, exist_ok=True)
    (rows["surface-library"] / "materials.json").write_text(json.dumps(content, indent=1))
    (rows["surface-library"] / "addresses.json").write_text(json.dumps(addresses, indent=1))
    (rows["surface-library"] / "left-out.json").write_text(json.dumps(left, indent=1))
    (rows["finish-route-palette"] / "palette.json").write_text(json.dumps(palette, indent=1))
    return rows


def take_data(row, folder):
    """The bench place's surface data (route_data.takes' input `surfaces`): the one take, its object words and kind."""
    take = row["id"]
    path = folder / "surfaces.json"
    path.write_text(json.dumps({"place": "bench163", "takes": {take: {"object": row["words"], "kind": row.get("kind"),
                                                                      "place": "bench163"}}}, indent=1))
    return path


def fitted_camera(model, close_up, row, folder):
    """camera.json in `folder`: the close-up's camera fitted from the model's outline against the close-up's alpha
    (close_up_fit.fitted_camera, round the close-up style's view of the row's size); its path."""
    from PIL import Image
    import close_up_fit
    import route_cast
    from score.stages.place_build import maker
    with Image.open(close_up) as picture:
        cut = np.asarray(picture.convert("RGBA").getchannel("A")) > 127
    turn, down = maker.close_up_view(row["size"])
    path = folder / "camera.json"
    path.write_text(json.dumps(close_up_fit.fitted_camera(route_cast.loaded(model), cut, turn, down), indent=1))
    return path


def finished(model, close_up, row, library, folder, ask=None):
    """The finish route's rows (views, list, split, parts) on one made model into `folder`, each row's output its own
    folder; the parts row's folder. `ask` replaces the list's ask (a test's); else the place line's (Claude)."""
    import score.stages.surfaces  # noqa: F401  (the stage first: its modules import one another through it)
    import claude_asks
    import route_list
    import route_parts
    import route_split
    import route_views
    rows = library_written(library, folder)
    inputs = {"surfaces": str(take_data(row, folder)), f"model {row['id']}": str(model),
              f"close-up {row['id']}": str(close_up), f"camera {row['id']}": str(fitted_camera(model, close_up, row,
                                                                                               folder)),
              **{name: str(path) for name, path in rows.items()}}
    params = {"objects": [row["id"]]}
    makes = (("finish-route-views", route_views.make_views),
             ("finish-route-list", claude_asks.asking_claude(route_list.make_list) if ask is None
              else asked_by(route_list, ask)),
             ("finish-route-split", route_split.make_split), ("surfaces-parts", route_parts.make_parts))
    for name, make in makes:
        out = folder / name
        out.mkdir()
        make(inputs, out, SEED, params)
        inputs[name] = str(out)
    parts = json.loads((folder / "surfaces-parts" / "parts.json").read_text())
    if row["id"] not in parts["takes"]:
        raise RuntimeError(f"no parts: {parts['left_out'].get(row['id'])}")
    return folder / "surfaces-parts"


def asked_by(module, ask):
    """The module's make with its `ask` replaced by `ask` for the call alone."""
    def made(inputs, out, seed, params):
        saved, module.ask = module.ask, ask
        try:
            return module.make_list(inputs, out, seed, params)
        finally:
            module.ask = saved
    return made


def family_of(address):
    """A library surface's family, the recipe its record names (an adopted surface's fitted one, a recipe entry's
    own), or None for one with none (painted for one model, a recipe gap) or no address."""
    if not address or not address.startswith("surface/"):
        return None
    recipe = records([address])[address].get("recipe")
    return recipe if isinstance(recipe, str) else (recipe or {}).get("recipe")


def same_family(pairs, made_surfaces, truth_surfaces):
    """{"same_family": the area share of the finish split's pairs (measures' finish `pairs`: each made part, its main
    truth finish, its area) whose made surface is of the truth surface's family, over the pairs whose truth surface
    has a family; "unjudged": the area share whose truth surface has none; "pairs": each with both families}."""
    rows, judged, unjudged, held = [], 0.0, 0.0, 0.0
    for pair in pairs:
        made = family_of(made_surfaces.get(pair["part"]))
        true = family_of(truth_surfaces[pair["material"]])
        rows.append({**pair, "family": made, "true_family": true})
        if true is None:
            unjudged += pair["area"]
            continue
        judged += pair["area"]
        held += pair["area"] if made == true else 0.0
    return {"same_family": round(held / judged, 4) if judged else None, "unjudged": round(unjudged, 4),
            "pairs": rows}


def linear_of(token):
    """A palette token's (sRGB hex) linear RGB."""
    srgb = np.array([int(token[index:index + 2], 16) for index in (1, 3, 5)], dtype=float) / 255
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def surface_look(record):
    """A library surface's own look (#172): {"colour": its recipe's colour (linear RGB; None for a recipe with no
    colour of its own or none), "metal", "roughness" (its recipe's, metal 0 where it names none), "class" (sim.py's
    surface_class)}."""
    from score.stages.place_build.maker import sim
    recipe = record.get("recipe")
    settings = (recipe.get("settings") or {}) if isinstance(recipe, dict) else {}
    return {"colour": settings.get("colour"), "metal": float(settings.get("metal", 0.0)),
            "roughness": settings.get("roughness"), "class": sim.surface_class(record)}


def own_spec(library, variant):
    """A bench library variant's own spec as it paints (its recipe's defaults under its own settings), {} for none."""
    for family in library["families"].values():
        if variant in family["variants"]:
            spec = family["variants"][variant]
            return {**library["recipes"].get(spec.get("recipe"), {}), **spec}
    return {}


def part_looks(folder, take):
    """{part: {"colour" linear RGB, "metal", "roughness", "class"}}: each finish part's look as the route set its
    surface on it (its row's token, metal and roughness: the list's settings, else, where the colour check moved its
    surface (route_settings.applied), that surface's own spec in the bench library) and its surface's class (sim.py's
    surface_class of its record; None for a surface outside the library)."""
    from score.stages.place_build.maker import sim
    part_of, surfaces = face_finishes(folder, take)
    listed = json.loads((folder / "surfaces-parts" / "parts.json").read_text())["takes"][take]["parts"]
    library = json.loads((folder / "surface-library" / "materials.json").read_text())
    held = records(sorted({address for address in surfaces.values() if address.startswith("surface/")}))
    found = {}
    for row in listed:
        settings = row.get("settings") or own_spec(library, row["judge"])
        record = held.get(surfaces[row["part"]])
        found[row["part"]] = {"colour": linear_of(settings["token"]).tolist() if settings.get("token") else None,
                              "metal": settings.get("metal"), "roughness": settings.get("roughness"),
                              "class": sim.surface_class(record) if record else None}
    return found


def face_finishes(folder, take):
    """(each face's part, {part: its library surface's address}) of a take the finish route parted: parts.npy in
    the model's own face order, the surface a variant of the bench library (addresses.json)."""
    parts = json.loads((folder / "surfaces-parts" / "parts.json").read_text())["takes"][take]
    addresses = json.loads((folder / "surface-library" / "addresses.json").read_text())
    part_of = np.load(folder / "surfaces-parts" / take / "parts.npy")
    return part_of, {row["part"]: addresses.get(row["judge"], row["judge"]) for row in parts["parts"]}


def z_up(vector):
    """glTF's Y-up (x, y, z) as Blender's Z-up after its glTF import: (x, -z, y)."""
    return [vector[0], -vector[2], vector[1]]


def slot_of(row):
    """The surface a finish part bakes as (route_bake.named_records): its settings' surface, else its own."""
    from score.stages.surfaces import route_settings
    return route_settings.settings_name(row["judge"], row["settings"]) if row.get("settings") else row["judge"]


def part_spec(library, row, colours, decals, out):
    """A finish part's recipe spec as the bake paints it: its surface's variant in the bench library in its own token,
    then its settings' token, roughness, metal and seed over it (route_settings.set_spec, as route_bake.baked_specs: its
    second shade moved with its colour; a part the colour check moved its surface's own), its
    slot's text decals (`decals`, the spec's). A colour setting its recipe needs (the library's `colour_settings`)
    that the variant names none of is the spec's own colour, as recipes.arguments gives a mottled or printed finish
    with no second shade its own: score_lib's recipe entries (finish.variant_of) carry a token alone (#182: the rack's
    painted_metal had no `bare`, the humidifier's perforated_metal no `second`); a printed or screen recipe
    (scene_library.PICTURED) with no picture of its own draws clear_picture's, written into `out`."""
    import library as surface_library
    from score.stages.surfaces import route_settings, scene_library
    settings = row.get("settings")
    own = surface_library.variants(library)[row["judge"]]["token"]
    for token in (own, *([settings["token"]] if settings else [])):
        colours.setdefault(token, surface_library.linear(token))
    spec = surface_library.spec(library, row["judge"], own, colours)
    if settings:
        spec = route_settings.set_spec(spec, settings, colours)
    spec.setdefault("seed", settings.get("seed", 0) if settings else 0)
    for setting in library.get("colour_settings", {}).get(spec["recipe"], []):
        spec.setdefault(setting, spec["colour"])
    if spec["recipe"] in scene_library.PICTURED and not spec.get("image"):
        spec["image"] = str(clear_picture(out))
    return {**spec, "decals": decals} if decals else spec


def mark_crop(picture, box):
    """A text mark's place in the look (`picture` RGBA, `box` [left, top, right, bottom] pixels) grown by READ_MARGIN
    of its longer side each way, laid on the look's grey, as PNG bytes."""
    import io
    from PIL import Image
    left, top, right, bottom = box
    grow = READ_MARGIN * max(right - left, bottom - top)
    cut = picture.crop((int(max(left - grow, 0)), int(max(top - grow, 0)), int(min(right + grow, picture.width)),
                        int(min(bottom + grow, picture.height))))
    laid = Image.new("RGBA", cut.size, (READ_GREY, READ_GREY, READ_GREY, 255))
    laid.alpha_composite(cut)
    found = io.BytesIO()
    laid.convert("RGB").save(found, format="PNG")
    return found.getvalue()


def reading_body(shown):
    """The ask that reads one mark's crop (`shown`, PNG bytes), as claude_code reads a Gemini generateContent body: the
    text printed there, never the words it should hold."""
    import base64
    schema = {"type": "OBJECT", "properties": {"reason": {"type": "STRING"}, "text": {"type": "STRING"}},
              "required": ["reason", "text"]}
    return {"contents": [{"role": "user", "parts": [
        {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(shown).decode()}}, {"text": READING}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def claude_read(bodies):
    """{key: the answer's JSON text, or why there is none} of the reading asks, sent to Claude on the subscription
    side by side (EUR 0)."""
    from score.adapters.models import claude_code
    return claude_code.asked(bodies, caller="bench-look-read")


def marks_read(folder, ask=None):
    """read.json in a drawn look's `folder` (#185: the sign's look drew a garbled "C" for "03" and no measure read
    text): each text mark of look.py's marks.json, its words and its place in look.png, read back by `ask`
    ({key: body} -> {key: answer JSON text or an exception}; a test's, else Claude's: no free local OCR is installed
    on this PC). [{"text", "box", "read": what was read there, None when unanswered, "why"}]."""
    from PIL import Image
    marks = json.loads((folder / "marks.json").read_text())
    with Image.open(folder / "look.png") as drawn:
        picture = drawn.convert("RGBA")
    answers = (ask or claude_read)({str(number): reading_body(mark_crop(picture, mark["box"]))
                                    for number, mark in enumerate(marks)}) if marks else {}
    found = []
    for number, mark in enumerate(marks):
        answer = answers[str(number)]
        read = None if isinstance(answer, Exception) else json.loads(answer)
        found.append({"text": mark["text"], "box": [round(value, 1) for value in mark["box"]],
                      "read": None if read is None else read["text"],
                      "why": repr(answer)[:300] if read is None else read["reason"]})
    (folder / "read.json").write_text(json.dumps(found, indent=1))
    return found


def clear_picture(out):
    """A one-pixel picture with nothing on it, in `out`: what a printed or screen recipe (scene_library.PICTURED) draws
    for a surface with no picture of its own (score_lib's `surface/printed`, a recipe entry), so its colour shows
    through (recipes.picture_on), its text the slot's decals (#182: the gas stove's control panel)."""
    from PIL import Image
    path = out / "clear.png"
    Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(path)
    return path


def look_axes(camera):
    """The look camera's (right, up, back) unit rows in Blender's frame from the close-up's `camera` (eye, aim, up):
    its own up, so a flat row seen from straight above has +y up (#159: a fixed +z up crossed with a straight-down
    view is zero, and the ceiling task light's look came out empty)."""
    back = np.subtract(camera["eye"], camera["aim"])
    back = back / np.linalg.norm(back)
    right = np.cross(camera["up"], back)
    right = right / np.linalg.norm(right)
    return right, np.cross(back, right), back


def look_job(folder, take, model, camera, out):
    """The finish's look drawn as the bake paints it (#182): one job for look.py, written into `out` with a mask a
    slot (`mask-<n>.png`), from the finish `folder`'s parts (surfaces-parts: parts.json and the take's texels.npz),
    each slot's recipe spec (part_spec) mixed by its texel mask on the made `model`'s own UVs, its own vertex normals
    kept (the model drawn whole, never part by part), from the close-up's `camera` ({eye, aim, up, fov}, Blender's
    frame); and the mesh alone (`bare.png`) for the holes check.
    A take with no texels.npz, or texels of more than one picture, has no look here: the raised reason says so."""
    import library as surface_library
    import route_texels
    from PIL import Image
    texels_file = folder / "surfaces-parts" / take / "texels.npz"
    if not texels_file.exists():
        raise RuntimeError(f"{take}: the finish wrote no texels.npz (the model has no picture)")
    with np.load(texels_file) as found:
        laid, pieces = route_texels.laid_pieces(dict(found))
    if len(pieces) != 1:
        raise RuntimeError(f"{take}: texels of {len(pieces)} pictures; the look draws one picture's UVs")
    listed = json.loads((folder / "surfaces-parts" / "parts.json").read_text())["takes"][take]
    library = json.loads((folder / "surface-library" / "materials.json").read_text())
    colours = surface_library.token_colours(library)
    rows = {row["part"]: row for row in listed["parts"]}
    decals = {}
    for decal in listed.get("decals", []):
        decals.setdefault(slot_of(rows[decal["part"]]), []).append({
            "image": str(folder / "surfaces-parts" / take / decal["picture"]), "at": z_up(decal["at"]),
            "normal": z_up(decal["normal"]), "up": z_up(decal["up"]), "size_m": decal["size"],
            "turn": decal.get("turn", 0.0), "layer": decal.get("layer", 0), "text": decal.get("text"),
            "ink": surface_library.linear(decal["ink_token"]) if decal.get("ink_token") else None})
    slots = sorted({slot_of(row) for row in rows.values()},
                   key=lambda slot: -sum(row["share"] for row in rows.values() if slot_of(row) == slot))
    surface_of_part = [slots.index(slot_of(rows[part])) if part in rows else -1 for part in range(max(rows) + 1)]
    masks = []
    for number, (slot, mask) in enumerate(zip(slots, route_texels.surface_masks(laid, surface_of_part, len(slots)))):
        Image.fromarray(mask).save(out / f"mask-{number}.png")
        row = next(row for row in rows.values() if slot_of(row) == slot)
        spec = part_spec(library, row, colours, decals.get(slot), out)
        masks.append({"slot": slot, "mask": str(out / f"mask-{number}.png"), "share": round(float(mask.mean() / 255), 4),
                      "spec": spec})
    job = {"glb": str(model), "masks": masks, **camera, "side": LOOK_SIDE, "samples": LOOK_SAMPLES,
           "out": str(out / "look.png"), "bare": str(out / "bare.png")}
    (out / "look.json").write_text(json.dumps(job, indent=1, default=float))
    return out / "look.json"
