"""The editor layer (#221): runs inside Unreal Editor's own Python and carries out plan.py's plan for one scene
package, into /Game/Score/<place>: the import's axes measured (frames' calibration box), our textures imported, our
master materials built from code and one Material Instance a look, every object's glTF imported (Nanite on the solid
ones) wearing those instances, an actor a copy, the lamps, sun, sky light and manual exposure, and the film path as a
Level Sequence's cine camera.

    UnrealEditor-Cmd <project>.uproject -run=pythonscript \
        -script="tools/unreal/scene/editor.py <package> <into> [<place>/film/path.json]"

Every decision is plan.py's (tested outside Unreal); this layer only calls the editor. No engine file or Epic asset
is named here but the engine's own classes: every picture and material is ours (the library rule, #217).
"""
import pathlib
import re
import sys

import unreal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import frames  # noqa: E402
import looks  # noqa: E402
import plan as planning  # noqa: E402

ROOT = "/Game/Score"
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDITING = unreal.MaterialEditingLibrary
SAMPLERS = {"colour": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, "data": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,
            "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL}
FILLER_OF = {"colour": "T_White", "data": "T_WhiteData", "normal": "T_FlatNormal"}
BLENDS = {"solid": unreal.BlendMode.BLEND_OPAQUE, "masked": unreal.BlendMode.BLEND_MASKED,
          "glass": unreal.BlendMode.BLEND_TRANSLUCENT}


def imported(files, destination):
    """The files imported into `destination` as automated import tasks: each file's imported asset objects."""
    tasks = []
    for file in files:
        task = unreal.AssetImportTask()
        for key, value in (("filename", str(file)), ("destination_path", destination), ("automated", True),
                           ("save", True), ("replace_existing", True)):
            task.set_editor_property(key, value)
        tasks.append(task)
    TOOLS.import_asset_tasks(tasks)
    return [[unreal.load_asset(path) for path in task.get_editor_property("imported_object_paths")] for task in tasks]


def measured_basis(into):
    """The glTF import's own axes: frames' calibration box imported and its bounds read (frames.basis_from_bounds)."""
    found = imported([frames.written_calibration(pathlib.Path(into) / "calibration.gltf")], f"{ROOT}/Calibration")[0]
    mesh = next(asset for asset in found if isinstance(asset, unreal.StaticMesh))
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


def mesh_made(mesh, place, instances):
    """One object's glTF imported (a Static Mesh, Nanite when the plan says; a character's a Skeletal Mesh), each
    material slot wearing its look's instance; the mesh asset."""
    found = imported([mesh["file"]], f"{ROOT}/{place}/Objects/{mesh['object']}")[0]
    kind = unreal.SkeletalMesh if mesh["character"] else unreal.StaticMesh
    asset = next(item for item in found if isinstance(item, kind))
    slots = {plain(slot): instances[look] for slot, look in mesh["slots"].items()}
    if mesh["character"]:
        materials = asset.get_editor_property("materials")
        for material in materials:
            material.set_editor_property("material_interface", slots[plain(material.get_editor_property(
                "material_slot_name"))])
        asset.set_editor_property("materials", materials)
    else:
        for number, material in enumerate(asset.get_editor_property("static_materials")):
            asset.set_material(number, slots[plain(material.get_editor_property("material_slot_name"))])
        settings = asset.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", mesh["nanite"])
        asset.set_editor_property("nanite_settings", settings)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    return asset


def placed(actor_plan, asset, place):
    """One copy spawned: its object's mesh at its laid transform, labelled by its name, in the place's folder."""
    transform = actor_plan["transform"]
    rotation = unreal.Quat(*transform["rotation"]).rotator()
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_object(
        asset, unreal.Vector(*transform["location"]), rotation)
    actor.set_actor_scale3d(unreal.Vector(transform["scale"], transform["scale"], transform["scale"]))
    actor.set_actor_label(actor_plan["name"])
    actor.set_folder_path(f"Score/{place}")
    return actor


def spawned(kind, location=(0.0, 0.0, 0.0), rotation=None):
    """An actor of `kind` spawned at `location` (cm), turned by a rotator {roll, pitch, yaw} when given."""
    turn = unreal.Rotator(roll=rotation["roll"], pitch=rotation["pitch"], yaw=rotation["yaw"]) if rotation \
        else unreal.Rotator()
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        kind, unreal.Vector(*location), turn)


def lamps_laid(lamps):
    """Every lamp a point light in lumens at its spot, radius and colour."""
    for lamp in lamps:
        light = spawned(unreal.PointLight, lamp["location"]).point_light_component
        light.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
        light.set_intensity(lamp["lumens"])
        light.set_editor_property("source_radius", lamp["radius"])
        light.set_light_color(unreal.LinearColor(*lamp["colour"], 1.0))


def bodies_laid(environment):
    """The sun and the moon each a directional light in lux, turned to shine from where it stands."""
    for body in (environment["sun"], environment["moon"]):
        if body:
            light = spawned(unreal.DirectionalLight, rotation=body["rotation"]).directional_light_component
            light.set_intensity(body["lux"])
            light.set_light_color(unreal.LinearColor(*body["colour"], 1.0))
            light.set_editor_property("light_source_angle", body["angle"])


def sky_laid(sky, place):
    """The sky's picture imported as a cube map and laid as the sky light, turned and at its strength."""
    cube = next(asset for asset in imported([sky["file"]], f"{ROOT}/{place}/Sky")[0]
                if isinstance(asset, unreal.TextureCube))
    light = spawned(unreal.SkyLight).light_component
    light.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    light.set_editor_property("cubemap", cube)
    light.set_editor_property("source_cubemap_angle", sky["turn"])
    light.set_intensity(sky["strength"])


def exposure_set(bias):
    """An unbound post-process volume holding the manual exposure at `bias` (EV), no physical camera's."""
    volume = spawned(unreal.PostProcessVolume)
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for key, value in (("override_auto_exposure_method", True),
                       ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("override_auto_exposure_bias", True), ("auto_exposure_bias", bias),
                       ("override_auto_exposure_apply_physical_camera_exposure", True),
                       ("auto_exposure_apply_physical_camera_exposure", False)):
        settings.set_editor_property(key, value)
    volume.set_editor_property("settings", settings)


def keyed(section, keys, values_of):
    """Each key's values (values_of(key): one a channel, in the section's channel order) keyed at its frame."""
    channels = section.get_all_channels()
    for key in keys:
        for channel, value in zip(channels, values_of(key)):
            channel.add_key(unreal.FrameNumber(key["frame"]), value)


def filmed(made):
    """The film path as a Level Sequence: a spawnable cine camera on our filmback, its location, rotation and focal
    length keyed every frame, and a camera cut on it the whole film."""
    shots = made["camera"]
    sequence = TOOLS.create_asset(f"LS_{made['place']}_film", f"{ROOT}/{made['place']}", unreal.LevelSequence,
                                  unreal.LevelSequenceFactoryNew())
    rate = unreal.FrameRate(shots["fps"], 1)
    sequence.set_display_rate(rate)
    sequence.set_tick_resolution(rate)
    sequence.set_playback_start(0)
    sequence.set_playback_end(shots["frames"])
    actor = spawned(unreal.CineCameraActor)
    lens = actor.get_cine_camera_component()
    filmback = lens.get_editor_property("filmback")
    filmback.set_editor_property("sensor_width", shots["filmback"][0])
    filmback.set_editor_property("sensor_height", shots["filmback"][1])
    lens.set_editor_property("filmback", filmback)
    binding = sequence.add_spawnable_from_instance(actor)
    actor.destroy_actor()
    motion = binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
    motion.set_range(0, shots["frames"])
    keyed(motion, shots["keys"], lambda key: key["location"] + [key["rotation"][axis] for axis in
                                                                 ("roll", "pitch", "yaw")])
    lens_binding = sequence.add_possessable(lens)
    lens_binding.set_parent(binding)
    focal = lens_binding.add_track(unreal.MovieSceneFloatTrack)
    focal.set_property_name_and_path("CurrentFocalLength", "CurrentFocalLength")
    focal_section = focal.add_section()
    focal_section.set_range(0, shots["frames"])
    keyed(focal_section, shots["keys"], lambda key: [key["focal_length"]])
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0, shots["frames"])
    cut.set_camera_binding_id(sequence.get_portable_binding_id(sequence, binding))
    unreal.EditorAssetLibrary.save_loaded_asset(sequence)
    return sequence


def main(arguments):
    """The package at arguments[0] carried into the open level, its textures staged under arguments[1], its film path
    (arguments[2]) as a Level Sequence when given."""
    package, into = arguments[0], arguments[1]
    made = planning.planned(package, into, arguments[2] if len(arguments) > 2 else None, measured_basis(into))
    textures = textures_made(made["textures"], made["place"])
    instances = {look["name"]: instance_made(look, made["place"], textures) for look in made["materials"]}
    meshes = {mesh["object"]: mesh_made(mesh, made["place"], instances) for mesh in made["meshes"]}
    for actor_plan in made["actors"]:
        placed(actor_plan, meshes[actor_plan["object"]], made["place"])
    lamps_laid(made["lamps"])
    bodies_laid(made["environment"])
    if made["environment"]["sky"]:
        sky_laid(made["environment"]["sky"], made["place"])
    exposure_set(made["environment"]["exposure_bias"])
    if made["camera"]:
        filmed(made)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.log(f"SCORE: {made['place']}: {len(meshes)} meshes, {len(made['actors'])} actors, "
               f"{len(instances)} material instances, camera {bool(made['camera'])}")


if __name__ == "__main__":
    main(sys.argv[1:])
