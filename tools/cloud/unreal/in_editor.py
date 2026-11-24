"""Inside Unreal's editor Python (on_card.py's commandlet, `-run=pythonscript`): make one Movie Render Queue config
asset a pass of the shot SCORE_UNREAL_SHOT names, from its recipe, and save it. The thin in-engine layer: what to
make (each pass's frames, folder and asset, the recipe's values) is decided in render.py, outside Unreal; this only
applies it through the `unreal` module, so nothing here runs without the engine.
"""
import json
import os

import unreal


def made_config(asset_path):
    """A new, empty config asset at `asset_path` (one left by an earlier run deleted first)."""
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.EditorAssetLibrary.delete_asset(asset_path)
    folder, name = asset_path.rsplit("/", 1)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    return tools.create_asset(name, folder, unreal.MoviePipelinePrimaryConfig, None)


def set_output(config, one_pass, recipe):
    """The pass's frames, folder and size, PNG frames named by their number."""
    output = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    output.output_directory = unreal.DirectoryPath(one_pass["folder"])
    output.output_resolution = unreal.IntPoint(recipe["width"], recipe["height"])
    output.use_custom_playback_range = True
    output.custom_start_frame = one_pass["start"]
    output.custom_end_frame = one_pass["end"]
    output.file_name_format = "{frame_number}"
    config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)


def set_sampling(config, recipe):
    """No anti-aliasing method, the recipe's samples and warm-up frames."""
    sampling = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    sampling.spatial_sample_count = recipe["spatial_samples"]
    sampling.temporal_sample_count = recipe["temporal_samples"]
    sampling.override_anti_aliasing = True
    sampling.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE
    sampling.engine_warm_up_count = recipe["warm_up_frames"]
    sampling.render_warm_up_count = recipe["warm_up_frames"]


def set_game(config, recipe):
    """Texture streaming and the cinematic quality settings, and the recipe's console variables."""
    game = config.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
    game.cinematic_quality_settings = recipe["cinematic_quality"]
    if not recipe["texture_streaming"]:
        game.texture_streaming = unreal.MoviePipelineTextureStreamingMethod.DISABLED
    variables = config.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    for name, value in recipe["console_variables"].items():
        variables.add_or_update_console_variable(name, float(value))


def main():
    with open(os.environ["SCORE_UNREAL_SHOT"]) as opened:
        shot = json.load(opened)
    for one_pass in shot["passes"]:
        config = made_config(one_pass["config"])
        set_output(config, one_pass, shot["recipe"])
        set_sampling(config, shot["recipe"])
        set_game(config, shot["recipe"])
        if not unreal.EditorAssetLibrary.save_loaded_asset(config):
            raise RuntimeError(f"the config {one_pass['config']} was not saved")
        unreal.log(f"score: made {one_pass['config']} ({one_pass['start']} to {one_pass['end']})")


main()
