"""The editor layer (#221): runs inside Unreal Editor's own Python and carries out plan.py's plan for one scene
package, into /Game/Score/<place>: the import's axes measured (frames' calibration box), our textures imported, our
master materials built from code and one Material Instance a look, every object's glTF imported (Nanite on the solid
ones) wearing those instances, an actor a copy, the lamps (each to its reach), sun, sky light, manual exposure and the
grade in place of Unreal's tonemapper, and the film path as a Level Sequence's cine camera.

    UnrealEditor-Cmd <project>.uproject -run=pythonscript \
        -script="tools/unreal/scene/editor.py <package> <into> [<place>/film/path.json]"

The level is made new at plan.level_path and every asset saved at the end; <into>/made.json says what was made, the
import's measured axes beside frames.BASIS and the faults (on_card.py reads it: a script that raised writes none,
whatever the commandlet's exit code). Each step logs "score: <step>" first, so a failure's log names where it stopped.
What the level cannot stand without (the axes, the level, the film's sequence, the save) raises; a look, an object or
a light the editor refused is a fault, logged "score: FAULT", left out and listed in made.json's `faults`, so one run
shows every call the engine refuses (render.py then calls the frames a run with faults, never a clean result).

Every decision is plan.py's (tested outside Unreal); this layer only calls the editor. No engine file or Epic asset
is named here but the engine's own classes: every picture and material is ours (the library rule, #217).
"""
import json
import pathlib
import re
import sys
import traceback

import unreal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import camera  # noqa: E402
import frames  # noqa: E402
import looks  # noqa: E402
import plan as planning  # noqa: E402

ROOT = planning.ROOT
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDITING = unreal.MaterialEditingLibrary
SAMPLERS = {"colour": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, "data": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL}
FILLER_OF = {"colour": "T_White", "data": "T_WhiteData", "normal": "T_FlatNormal"}
BLENDS = {"solid": unreal.BlendMode.BLEND_OPAQUE, "masked": unreal.BlendMode.BLEND_MASKED,
          "glass": unreal.BlendMode.BLEND_TRANSLUCENT}


def combining():
    """Interchange's generic assets pipeline asked to combine an object's meshes into one (its nodes' transforms
    baked in). UE 5.8 still gave one asset a mesh node (#222, run 8), so an object may come in as several parts
    (parts_of), each laid at the object's transform."""
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    meshes = pipeline.get_editor_property("mesh_pipeline")
    meshes.set_editor_property("combine_static_meshes_behavior", unreal.InterchangeCombineStaticMeshesBehavior.ALL)
    return pipeline


def imported(files, destination, options=None):
    """The files imported into `destination` as automated import tasks (under `options`, an import pipeline, when
    given): each file's imported asset objects."""
    tasks = []
    for file in files:
        task = unreal.AssetImportTask()
        for key, value in (("filename", str(file)), ("destination_path", destination), ("automated", True),
                           ("save", True), ("replace_existing", True)):
            task.set_editor_property(key, value)
        if options is not None:
            task.set_editor_property("options", options)
        tasks.append(task)
    TOOLS.import_asset_tasks(tasks)
    return [[unreal.load_asset(path) for path in task.get_editor_property("imported_object_paths")] for task in tasks]


def only(found, kind, what):
    """The one asset of `kind` among an import's assets; refused when there is none or more than one."""
    assets = [asset for asset in found if isinstance(asset, kind)]
    if len(assets) != 1:
        raise RuntimeError(f"{what}: {len(assets)} {kind.__name__} assets imported, one expected "
                           f"({[asset.get_path_name() for asset in assets][:6]})")
    return assets[0]


def parts_of(found, kind, what, most):
    """The assets of `kind` among an import's assets, the object's parts: at least one and at most `most` (its
    glTF's mesh nodes, plan.py's `parts`); refused otherwise, naming what came."""
    assets = [asset for asset in found if isinstance(asset, kind)]
    if not 1 <= len(assets) <= max(most, 1):
        raise RuntimeError(f"{what}: {len(assets)} {kind.__name__} assets imported, 1 to {max(most, 1)} expected "
                           f"({[asset.get_path_name() for asset in assets][:6]})")
    return assets


def measured_basis(into):
    """The glTF import's own axes: frames' calibration box imported and its bounds read (frames.basis_from_bounds)."""
    found = imported([frames.written_calibration(pathlib.Path(into) / "calibration.gltf")], f"{ROOT}/Calibration",
                     combining())[0]
    mesh = only(found, unreal.StaticMesh, "the calibration box")
    box = mesh.get_bounding_box()
    return frames.basis_from_bounds([box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z])


def textures_made(listed, place):
    """Every texture of the plan imported and read as it is meant (colour as sRGB, data linear, a normal as a normal
    map), never streamed (a film reads every map at its full size); {name: Texture2D}."""
    made = {}
    for about, found in zip(listed, imported([about["file"] for about in listed], f"{ROOT}/{place}/Textures")):
        texture = next(asset for asset in found if isinstance(asset, unreal.Texture2D))
        texture.set_editor_property("srgb", about["srgb"])
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP
                                    if about["normal"] else unreal.TextureCompressionSettings.TC_DEFAULT
                                    if about["srgb"] else unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("never_stream", True)
        unreal.EditorAssetLibrary.save_loaded_asset(texture)
        made[about["name"]] = texture
    return made


def kind_of(colour, normal):
    """How a slot's picture is read: "normal", "colour" (sRGB) or "data" (linear)."""
    return "normal" if normal else "colour" if colour else "data"


def expression(material, kind, at, **properties):
    """One expression of `kind` in the material at `at` (x, y), its properties set."""
    made = EDITING.create_material_expression(material, kind, at[0], at[1])
    for key, value in properties.items():
        made.set_editor_property(key, value)
    return made


def multiplied(material, first, first_out, second, second_out, at):
    """A Multiply of two expressions' outputs."""
    made = expression(material, unreal.MaterialExpressionMultiply, at)
    EDITING.connect_material_expressions(first, first_out, made, "A")
    EDITING.connect_material_expressions(second, second_out, made, "B")
    return made


def master(kind, textures):
    """Our master material of `kind` (looks.MASTERS), built from code the first time: each glTF picture slot a
    texture parameter (our filler by default) times its factor, as glTF reads a material."""
    path = f"{ROOT}/Masters/M_Score_{kind}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    material = TOOLS.create_asset(f"M_Score_{kind}", f"{ROOT}/Masters", unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property("blend_mode", BLENDS[kind])
    material.set_editor_property("two_sided", True)
    maps = {parameter: expression(material, unreal.MaterialExpressionTextureSampleParameter2D, (-900, 300 * number),
                                  parameter_name=parameter, sampler_type=SAMPLERS[kind_of(colour, normal)],
                                  texture=textures[FILLER_OF[kind_of(colour, normal)]])
            for number, (_, parameter, colour, normal) in enumerate(looks.SLOTS)}
    colour = expression(material, unreal.MaterialExpressionVectorParameter, (-900, -300), parameter_name="BaseColor")
    glow = expression(material, unreal.MaterialExpressionVectorParameter, (-900, 1500), parameter_name="Emissive")
    metal, rough = (expression(material, unreal.MaterialExpressionScalarParameter, (-900, -500 - 100 * number),
                               parameter_name=name) for number, name in enumerate(("Metallic", "Roughness")))
    EDITING.connect_material_property(multiplied(material, maps["BaseColorMap"], "RGB", colour, "", (-400, 0)), "",
                                      unreal.MaterialProperty.MP_BASE_COLOR)
    EDITING.connect_material_property(multiplied(material, maps["MetalRoughnessMap"], "B", metal, "", (-400, 200)), "",
                                      unreal.MaterialProperty.MP_METALLIC)
    EDITING.connect_material_property(multiplied(material, maps["MetalRoughnessMap"], "G", rough, "", (-400, 400)), "",
                                      unreal.MaterialProperty.MP_ROUGHNESS)
    EDITING.connect_material_property(maps["NormalMap"], "RGB", unreal.MaterialProperty.MP_NORMAL)
    EDITING.connect_material_property(multiplied(material, maps["EmissiveMap"], "RGB", glow, "", (-400, 600)), "",
                                      unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    EDITING.connect_material_property(maps["OcclusionMap"], "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if kind == "masked":
        EDITING.connect_material_property(multiplied(material, maps["BaseColorMap"], "A", colour, "A", (-400, 800)),
                                          "", unreal.MaterialProperty.MP_OPACITY_MASK)
    if kind == "glass":
        material.set_editor_property("translucency_lighting_mode",
                                     unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        for number, (name, slot) in enumerate((("Opacity", unreal.MaterialProperty.MP_OPACITY),
                                                ("IOR", unreal.MaterialProperty.MP_REFRACTION))):
            EDITING.connect_material_property(expression(material, unreal.MaterialExpressionScalarParameter,
                                                         (-400, 1000 + 200 * number), parameter_name=name), "", slot)
    EDITING.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    return material


def instance_made(look, place, textures):
    """One look as a Material Instance of its master: its factors, pictures, sidedness and a masked look's cutoff."""
    made = TOOLS.create_asset(look["name"], f"{ROOT}/{place}/Looks", unreal.MaterialInstanceConstant,
                              unreal.MaterialInstanceConstantFactoryNew())
    EDITING.set_material_instance_parent(made, master(look["master"], textures))
    for name, value in look["vectors"].items():
        EDITING.set_material_instance_vector_parameter_value(made, name, unreal.LinearColor(*value))
    for name, value in look["scalars"].items():
        if name != "AlphaCutoff":
            EDITING.set_material_instance_scalar_parameter_value(made, name, value)
    for name, texture in look["textures"].items():
        EDITING.set_material_instance_texture_parameter_value(made, name, textures[texture])
    overrides = made.get_editor_property("base_property_overrides")
    overrides.set_editor_property("override_two_sided", True)
    overrides.set_editor_property("two_sided", look["two_sided"])
    if "AlphaCutoff" in look["scalars"]:
        overrides.set_editor_property("override_opacity_mask_clip_value", True)
        overrides.set_editor_property("opacity_mask_clip_value", look["scalars"]["AlphaCutoff"])
    made.set_editor_property("base_property_overrides", overrides)
    EDITING.update_material_instance(made)
    unreal.EditorAssetLibrary.save_loaded_asset(made)
    return made


def plain(name):
    """A slot name as the import may have cleaned it: every run of other than letters and digits one underscore."""
    return re.sub(r"[^A-Za-z0-9]+", "_", str(name)).strip("_").lower()


def slot_look(slots, slot_name, what):
    """The instance a mesh's material slot wears, by its name as the import cleaned it; refused, naming the plan's
    slots, when the import named it otherwise."""
    if plain(slot_name) not in slots:
        raise RuntimeError(f"{what}: the import's slot {slot_name!r} is none of the plan's {sorted(slots)}")
    if slots[plain(slot_name)] is None:
        raise RuntimeError(f"{what}: the look its slot {slot_name!r} wears was not made")
    return slots[plain(slot_name)]


def mesh_made(mesh, place, instances):
    """One object's glTF imported (Static Meshes, Nanite when the plan says; a character's Skeletal Meshes, sharing
    one skeleton, standing unposed until its plays are keyed), each part's material slots wearing their looks'
    instances; the parts' mesh assets."""
    found = imported([mesh["file"]], f"{ROOT}/{place}/Objects/{mesh['object']}", combining())[0]
    slots = {plain(slot): instances[look] for slot, look in mesh["slots"].items()}
    return [part_made(asset, mesh, slots) for asset in parts_of(
        found, unreal.SkeletalMesh if mesh["character"] else unreal.StaticMesh, mesh["object"], mesh["parts"])]


def part_made(asset, mesh, slots):
    """One imported part of an object: its material slots wearing their looks' instances (Nanite on a Static Mesh
    when the plan says), saved; the asset."""
    if mesh["character"]:
        materials = asset.get_editor_property("materials")
        for material in materials:
            material.set_editor_property("material_interface", slot_look(
                slots, material.get_editor_property("material_slot_name"), mesh["object"]))
        asset.set_editor_property("materials", materials)
    else:
        for number, material in enumerate(asset.get_editor_property("static_materials")):
            asset.set_material(number, slot_look(slots, material.get_editor_property("material_slot_name"),
                                                 mesh["object"]))
        settings = asset.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", mesh["nanite"])
        asset.set_editor_property("nanite_settings", settings)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    return asset


def placed(actor_plan, assets, place):
    """One copy spawned: an actor a part of its object (placed_part), each at the copy's laid transform."""
    for asset in assets:
        placed_part(actor_plan, asset, place, actor_plan["name"] if len(assets) == 1
                    else f"{actor_plan['name']}_{asset.get_name()}")


def placed_part(actor_plan, asset, place, label):
    """One part of a copy spawned: its mesh at the copy's laid transform, labelled `label`, in the place's folder.

    A Static Mesh goes in as an empty StaticMeshActor given its mesh after the spawn, so the spawn never tests the
    mesh's collision against what is already laid: spawn_actor_from_object returned None for 11 wall-mounted copies
    on one facade (#222, run 6) while the same mesh at the same turn spawned elsewhere, the mark of a spawn refused
    for encroaching. A character's Skeletal Mesh goes in the same way, as an empty SkeletalMeshActor given its mesh
    (the mesh's own actor factory gave no actor for all 12 walkers, #222 run 9). A spawn that still gives no actor
    raises, naming the spot (the engine's LogSpawn line in Saved/Logs says why)."""
    transform = actor_plan["transform"]
    location = unreal.Vector(*transform["location"])
    rotation = unreal.Quat(*transform["rotation"]).rotator()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if isinstance(asset, unreal.StaticMesh):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        if actor is not None and not actor.get_editor_property("static_mesh_component").set_static_mesh(asset):
            raise RuntimeError(f"{asset.get_path_name()} was not set on the spawned StaticMeshActor")
    elif isinstance(asset, unreal.SkeletalMesh):
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, location, rotation)
        if actor is not None:
            skin = actor.get_editor_property("skeletal_mesh_component")
            skin.set_skeletal_mesh_asset(asset)
            if skin.get_skeletal_mesh_asset() != asset:
                raise RuntimeError(f"{asset.get_path_name()} was not set on the spawned SkeletalMeshActor")
    else:
        raise RuntimeError(f"{asset.get_path_name()} is a {type(asset).__name__}, not a Static or Skeletal Mesh")
    if actor is None:
        raise RuntimeError(f"the editor spawned no actor for {asset.get_path_name()} at {list(transform['location'])} "
                           f"turned {list(transform['rotation'])}")
    actor.set_actor_scale3d(unreal.Vector(transform["scale"], transform["scale"], transform["scale"]))
    actor.set_actor_label(label)
    actor.set_folder_path(f"Score/{place}")
    return actor


def spawned(kind, location=(0.0, 0.0, 0.0), rotation=None):
    """An actor of `kind` spawned at `location` (cm), turned by a rotator {roll, pitch, yaw} when given."""
    turn = unreal.Rotator(roll=rotation["roll"], pitch=rotation["pitch"], yaw=rotation["yaw"]) if rotation \
        else unreal.Rotator()
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        kind, unreal.Vector(*location), turn)


def movable(actor):
    """A light's actor made Movable (Lumen lights it with no built lighting, and a Stationary light past four
    overlapping loses its shadows); its light component."""
    light = actor.get_editor_property("light_component")
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    return light


def lamps_laid(lamps):
    """Every lamp a point light in lumens at its spot, radius and colour."""
    for lamp in lamps:
        light = movable(spawned(unreal.PointLight, lamp["location"]))
        light.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
        light.set_intensity(lamp["lumens"])
        light.set_editor_property("source_radius", lamp["radius"])
        light.set_editor_property("attenuation_radius", lamp["reach"])
        light.set_light_color(unreal.LinearColor(*lamp["colour"], 1.0))


def bodies_laid(environment):
    """The sun and the moon each a directional light in lux, turned to shine from where it stands."""
    for body in (environment["sun"], environment["moon"]):
        if body:
            light = movable(spawned(unreal.DirectionalLight, rotation=body["rotation"]))
            light.set_intensity(body["lux"])
            light.set_light_color(unreal.LinearColor(*body["colour"], 1.0))
            light.set_editor_property("light_source_angle", body["angle"])


def sky_laid(sky, place):
    """The sky's picture (a night's its even ambient) imported as a cube map and laid as the sky light, turned and at
    its strength (Unreal's units, layout.environment), captured."""
    cube = next(asset for asset in imported([sky["file"]], f"{ROOT}/{place}/Sky")[0]
                if isinstance(asset, unreal.TextureCube))
    light = movable(spawned(unreal.SkyLight))
    light.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    light.set_editor_property("cubemap", cube)
    light.set_editor_property("source_cubemap_angle", sky["turn"])
    light.set_intensity(sky["strength"])
    light.recapture_sky()


def grade_picture(grade, place):
    """The package's grade picture imported as a lookup table: read as it is written (no sRGB), unfiltered across
    mips (none), clamped at its edges, never compressed or streamed."""
    texture = next(asset for asset in imported([grade["file"]], f"{ROOT}/{place}/Grade")[0]
                   if isinstance(asset, unreal.Texture2D))
    for key, value in (("srgb", False), ("compression_settings", unreal.TextureCompressionSettings.TC_HDR),
                       ("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
                       ("filter", unreal.TextureFilter.TF_BILINEAR), ("address_x", unreal.TextureAddress.TA_CLAMP),
                       ("address_y", unreal.TextureAddress.TA_CLAMP), ("never_stream", True)):
        texture.set_editor_property(key, value)
    unreal.EditorAssetLibrary.save_loaded_asset(texture)
    return texture


def custom_input(name):
    """A Custom expression's input called `name`: CustomInput shows Python no Blueprint property, so its constructor
    takes no keywords (run 12: "call() takes at most 0 arguments") and its name is set as an editor property."""
    made = unreal.CustomInput()
    made.set_editor_property("input_name", name)
    return made


def graded(grade, place):
    """The post-process material that replaces Unreal's tonemapper with the final render's grade (layout.grade_code:
    the scene colour, or the background where nothing stands, exposed and looked up in the grade picture)."""
    material = TOOLS.create_asset("M_Score_grade", f"{ROOT}/{place}", unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    material.set_editor_property("blendable_location", unreal.BlendableLocation.BL_REPLACING_TONEMAPPER)
    custom = expression(material, unreal.MaterialExpressionCustom, (-300, 0), code=grade["code"],
                        output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, description="score grade",
                        inputs=[custom_input(name) for name in ("Color", "Depth", "Grade")])
    colour = expression(material, unreal.MaterialExpressionSceneTexture, (-700, -200),
                        scene_texture_id=unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    depth = expression(material, unreal.MaterialExpressionSceneTexture, (-700, 0),
                       scene_texture_id=unreal.SceneTextureId.PPI_SCENE_DEPTH)
    picture = expression(material, unreal.MaterialExpressionTextureObject, (-700, 200),
                         texture=grade_picture(grade, place))
    for source, output, name in ((colour, "Color", "Color"), (depth, "Color", "Depth"), (picture, "", "Grade")):
        if not EDITING.connect_material_expressions(source, output, custom, name):
            raise RuntimeError(f"the grade's {name} input was not connected")
    if not EDITING.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("the grade's output was not connected")
    EDITING.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    return material


def exposure_set(bias, grade=None):
    """An unbound post-process volume holding the manual exposure at `bias` (EV), no physical camera's, and the
    `grade` material (graded) in place of Unreal's tonemapper when given."""
    volume = spawned(unreal.PostProcessVolume)
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for key, value in (("override_auto_exposure_method", True),
                       ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("override_auto_exposure_bias", True), ("auto_exposure_bias", bias),
                       ("override_auto_exposure_apply_physical_camera_exposure", True),
                       ("auto_exposure_apply_physical_camera_exposure", False)):
        settings.set_editor_property(key, value)
    if grade is not None:
        settings.set_editor_property("weighted_blendables", unreal.WeightedBlendables(
            array=[unreal.WeightedBlendable(weight=1.0, object=grade)]))
    volume.set_editor_property("settings", settings)


def keyed(section, keys, values_of):
    """Each key's values (values_of(key): one a channel, in the section's channel order) keyed at its frame; refused
    (camera.unlanded) when the section has fewer channels than a key's values or a channel did not take every key,
    which a plain zip let through silently (#222, runs 9 and 10: the camera stood at the level's origin, unkeyed)."""
    channels = list(section.get_all_channels())
    for key in keys:
        for channel, value in zip(channels, values_of(key)):
            channel.add_key(unreal.FrameNumber(key["frame"]), value)
    fault = camera.unlanded(len(values_of(keys[0])), [len(channel.get_keys()) for channel in channels], len(keys))
    if fault:
        raise RuntimeError(fault)


def filmed(made, faults):
    """The film path as a Level Sequence: a cine camera in the level on our filmback, standing at the first key with
    its focal length (so the first frame is the path's even when the sequence does not move it), possessed by the
    sequence, its location, rotation and focal length keyed every frame (keys that did not land are a fault), and a
    camera cut on it the whole film."""
    shots = made["camera"]
    first = shots["keys"][0]
    folder, name = planning.sequence_path(made["place"]).split(".")[0].rsplit("/", 1)
    sequence = TOOLS.create_asset(name, folder, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    rate = unreal.FrameRate(shots["fps"], 1)
    sequence.set_display_rate(rate)
    sequence.set_tick_resolution(rate)
    sequence.set_playback_start(0)
    sequence.set_playback_end(shots["frames"])
    actor = spawned(unreal.CineCameraActor, first["location"], first["rotation"])
    actor.set_actor_label(f"{made['place']}_film_camera")
    lens = actor.get_cine_camera_component()
    lens.set_editor_property("current_focal_length", first["focal_length"])
    filmback = lens.get_editor_property("filmback")
    filmback.set_editor_property("sensor_width", shots["filmback"][0])
    filmback.set_editor_property("sensor_height", shots["filmback"][1])
    lens.set_editor_property("filmback", filmback)
    binding = sequence.add_possessable(actor)
    motion = binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
    motion.set_range(0, shots["frames"])
    attempted(faults, "camera motion keys", keyed, motion, shots["keys"],
              lambda key: key["location"] + [key["rotation"][axis] for axis in ("roll", "pitch", "yaw")])
    lens_binding = sequence.add_possessable(lens)
    lens_binding.set_parent(binding)
    focal = lens_binding.add_track(unreal.MovieSceneFloatTrack)
    focal.set_property_name_and_path("CurrentFocalLength", "CurrentFocalLength")
    focal_section = focal.add_section()
    focal_section.set_range(0, shots["frames"])
    attempted(faults, "camera focal keys", keyed, focal_section, shots["keys"], lambda key: [key["focal_length"]])
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0, shots["frames"])
    cut.set_camera_binding_id(sequence.get_portable_binding_id(sequence, binding))
    unreal.EditorAssetLibrary.save_loaded_asset(sequence)
    return sequence


def attempted(faults, what, call, *arguments):
    """call(*arguments), or None with its error added to `faults` as {what, error} and logged."""
    try:
        return call(*arguments)
    except Exception as error:  # noqa: BLE001 - every refusal is listed in made.json and fails the result
        here = [frame for frame in traceback.extract_tb(error.__traceback__) if frame.filename == __file__]
        faults.append({"what": what, "error": f"{type(error).__name__}: {error}",
                       "line": here[-1].lineno if here else None})
        unreal.log_error(f"score: FAULT {what}: {type(error).__name__}: {error}")
        return None


def step(name):
    """Log the step about to run, so a failure's log names where it stopped."""
    unreal.log(f"score: {name}")


def level_made(place):
    """A new level at plan.level_path, open (one an earlier run left replaced)."""
    path = planning.level_path(place)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level(path):
        raise RuntimeError(f"the level {path} was not made")


def saved(place):
    """The level and every changed asset saved; refused when one was not."""
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
        raise RuntimeError(f"the level {planning.level_path(place)} was not saved")
    if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
        raise RuntimeError("the changed assets were not all saved")


def place_laid(made, faults):
    """One planned place carried into the open level: its textures, one instance a look, its objects, an actor a copy
    and its lamps, under /Game/Score/<place>, each refusal a fault named for the place; {meshes, parts, materials,
    textures} made."""
    place = made["place"]
    step(f"{place}: {len(made['textures'])} textures")
    textures = textures_made(made["textures"], place)
    step(f"{place}: {len(made['materials'])} material instances")
    instances = {look["name"]: attempted(faults, f"{place} look {look['name']}", instance_made, look, place, textures)
                 for look in made["materials"]}
    step(f"{place}: {len(made['meshes'])} meshes")
    meshes = {mesh["object"]: attempted(faults, f"{place} object {mesh['object']}", mesh_made, mesh, place, instances)
              for mesh in made["meshes"]}
    step(f"{place}: {len(made['actors'])} actors and {len(made['lamps'])} lamps")
    for actor_plan in made["actors"]:
        if meshes[actor_plan["object"]] is not None:
            attempted(faults, f"{place} actor {actor_plan['name']}", placed, actor_plan, meshes[actor_plan["object"]],
                      place)
    attempted(faults, f"{place} lamps", lamps_laid, made["lamps"])
    return {"meshes": sum(mesh is not None for mesh in meshes.values()),
            "parts": sum(len(mesh) for mesh in meshes.values() if mesh is not None),
            "materials": sum(look is not None for look in instances.values()), "textures": len(textures)}


def among_of(arguments):
    """The words of the editor's arguments: (the positional ones, the neighbour packages each `--among=<folder>`)."""
    among = [word.split("=", 1)[1] for word in arguments if word.startswith("--among=")]
    return [word for word in arguments if not word.startswith("--among=")], among


def main(arguments):
    """The package at arguments[0] carried into a new level, its textures staged under arguments[1], its film path
    (arguments[2]) as a Level Sequence when given, and each `--among=<package>` (a neighbour place the area seats in
    the same frame) laid beside it: its objects, looks and lamps, the main place's sky, exposure, grade and camera
    alone; <into>/made.json written last."""
    arguments, among = among_of(arguments)
    package, into = arguments[0], pathlib.Path(arguments[1])
    into.mkdir(parents=True, exist_ok=True)
    step("measuring the import's axes")
    basis = measured_basis(into)
    made = planning.planned(package, into, arguments[2] if len(arguments) > 2 else None, basis)
    neighbours = [planning.planned(folder, into / "among" / str(number), None, basis)
                  for number, folder in enumerate(among)]
    step(f"a new level for {made['place']}")
    level_made(made["place"])
    faults = []
    counts = place_laid(made, faults)
    beside = [dict(place_laid(neighbour, faults), place=neighbour["place"], actors=len(neighbour["actors"]),
                   lamps=len(neighbour["lamps"])) for neighbour in neighbours]
    step("the sun, sky and exposure")
    attempted(faults, "sun and moon", bodies_laid, made["environment"])
    if made["environment"]["sky"]:
        attempted(faults, "sky", sky_laid, made["environment"]["sky"], made["place"])
    grade = attempted(faults, "grade", graded, made["environment"]["grade"], made["place"]) \
        if made["environment"]["grade"] else None
    attempted(faults, "exposure", exposure_set, made["environment"]["exposure_bias"], grade)
    if made["camera"]:
        step("the film's Level Sequence")
        filmed(made, faults)
    step("saving")
    saved(made["place"])
    summary = dict(counts, place=made["place"], level=planning.level_path(made["place"]),
                   sequence=planning.sequence_path(made["place"]) if made["camera"] else None,
                   measured_basis=[list(row) for row in basis], expected_basis=[list(row) for row in frames.BASIS],
                   basis_as_expected=[list(row) for row in basis] == [list(row) for row in frames.BASIS],
                   actors=len(made["actors"]), lamps=len(made["lamps"]),
                   camera_first=made["camera"]["keys"][0] if made["camera"] else None, among=beside,
                   left_out=made["left_out"], faults=faults)
    (into / "made.json").write_text(json.dumps(summary, indent=1))
    unreal.log(f"score: made {json.dumps(summary)}")


if __name__ == "__main__":
    main(sys.argv[1:])
