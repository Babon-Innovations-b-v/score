"""Unreal renders (render.py, on_card.py, _twice.py, _cost.py): a shot goes to the cluster as one job on one card
class, refused before anything is sent when its project cannot ray-trace on Linux; the job names a shader cache by
engine, RHI and the project's shader settings alone; on the card the editor runs headless through Movie Render Queue
and Vulkan's ray tracing is checked first; what comes back is checked twice (a tile darker in one render is a fault)
and priced a frame. Nothing is rented and no engine runs: the cluster and the provider are stood in for, the frames
are pictures drawn here, every expected number worked by hand.

Breaks, each applied once and seen red (2026-11-24):
- `project_refusal`'s REFUSED check dropped -> a project still targeting SM5 is sent.
- `ddc_name` hashes the whole ini (`settings = sorted(text.splitlines())`) -> a map setting moves the cache.
- `ddc_name` leaves the engine out of the name -> 5.8.3's cache is taken for 5.8.4's.
- `job`'s check frames dropped from the minutes -> 161, not 164.
- `render_command`'s "-RenderOffscreen" dropped -> the render wants a window.
- `vulkan_missing` checks only the first extension -> a driver without position fetch passes.
- `driver_refusal`'s `node != baked` dropped -> a node on another driver runs libraries that do not load.
- `vulkan_refusal` drops vulkaninfo's stderr -> the failure no longer says why Vulkan would not start.
- `ddc_folder`'s `.parent` dropped -> the cache goes inside the CUDA cache's folder.
- `_twice.compare`'s `np.abs` dropped -> a darker full render is no fault.
- `_twice.check`'s `len(names) == frames` dropped -> a check pass that made fewer frames counts as same.
- `_cost.frame_cost` divides by the check pass's frames -> EUR 0.375 a frame, not 0.03125.
- `render` sends before `project_refusal` -> a refused project is bought.
- `project_made` writes MADE_SETTINGS alone (2026-11-24) -> a made project fails its own refusal check.
- `plugins_held` keeps every plugin -> an image without EditorScriptingUtilities stops the editor.
- `object_path` returns the path unchanged -> Movie Render Queue is given /Game/ScoreRender/Check, no object.
- `job`'s scene inputs dropped -> the package never goes up with a --package shot.
- `closed` skips `logs_kept` (2026-11-24) -> a failed run comes back without the editor's logs.
- `scene_record` refuses a non-zero exit -> a level made with faults stops the render (#222, run 6).
- `render` skips `card_failure` -> a run that stopped on the card is priced and checked as frames.
- `cache_dropped` keeps the cache of a killed server -> a half-written shader cache is packed (#222, run 7).
"""
import json
import pathlib
import sys
import types

import numpy as np
import pytest
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _cost  # noqa: E402
import _twice  # noqa: E402
import on_card  # noqa: E402
import render  # noqa: E402

GOOD = """; the project's engine settings
[/Script/LinuxTargetPlatform.LinuxTargetSettings]
-TargetedRHIs=SF_VULKAN_SM5
+TargetedRHIs=SF_VULKAN_SM6

[/Script/Engine.RendererSettings]
r.RayTracing=True
r.SkinCache.CompileShaders=True
r.Lumen.HardwareRayTracing=True
r.DynamicGlobalIlluminationMethod=1
r.ReflectionMethod=1

[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=/Game/Place/Street
"""
REORDERED = """[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=/Game/Place/Other
[/Script/Engine.RendererSettings]
; a comment moves nothing
r.ReflectionMethod=1
r.DynamicGlobalIlluminationMethod=1
r.Lumen.HardwareRayTracing=True
r.SkinCache.CompileShaders=True
r.RayTracing=True
[/Script/LinuxTargetPlatform.LinuxTargetSettings]
+TargetedRHIs=SF_VULKAN_SM6
-TargetedRHIs=SF_VULKAN_SM5
"""
VULKANINFO = """GPU0:
VkPhysicalDeviceProperties:
	deviceName        = NVIDIA L40S
Device Extensions:
	VK_KHR_acceleration_structure     : extension revision 13
	VK_KHR_ray_query                  : extension revision 1
	VK_KHR_ray_tracing_pipeline       : extension revision 1
	VK_KHR_shader_atomic_int64        : extension revision 1
"""
RECORD = {"card": "NVIDIA L40S", "job_seconds": 600.0, "ddc": {"folder": "/c", "bytes_before": 0, "bytes_after": 5},
          "passes": {"config": {"seconds": 40.0}, "full": {"seconds": 900.0, "frames": 96},
                     "check": {"seconds": 80.0, "frames": 8}}}


def frame(path, values):
    Image.fromarray(np.clip(values, 0, 255).astype(np.uint8)).convert("RGB").save(path)


def frames(folder, names, change=None):
    """Grey 128x96 frames; `change` alters one frame's pixels by name."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        values = np.full((96, 128), 128.0)
        if change and name in change:
            values = change[name](values)
        frame(folder / name, values)
    return folder


def darkened(values):
    values = values.copy()
    values[32:96, 64:128] = 26.0  # a 64x64 rectangle, four tiles, at 0.1 against 0.5
    return values


def noisy(values):
    return values + np.random.default_rng(7).integers(-3, 4, values.shape)  # about +-0.01 a pixel


def project(folder, ini=GOOD):
    (folder / "Config").mkdir(parents=True)
    (folder / "Config/DefaultEngine.ini").write_text(ini)
    (folder / "Street.uproject").write_text("{}")
    return folder


def kept_cache(folder):
    """A shader cache folder holding one file and one folder, as the editor leaves it."""
    (folder / "Zen").mkdir(parents=True)
    (folder / "Zen/blob").write_bytes(b"x")
    (folder / "index").write_bytes(b"y")
    return folder


def test_a_shot_goes_up_as_one_ray_traced_job_and_comes_back_checked_twice_and_priced(tmp_path, monkeypatch):
    names = [f"{number:04d}.png" for number in range(8)]
    full = frames(tmp_path / "out/full", names, {"0001.png": noisy})
    good = project(tmp_path / "good")
    shot_file = tmp_path / "shot.json"
    sent = []

    def cluster_run(kind, jobs, who, classes, image, name):
        """The cluster stood in for: the job's out folder comes back as on_card.py leaves it."""
        sent.append({"kind": kind, "who": who, "classes": classes, "image": image, "job": jobs[0],
                     "shot": json.loads(pathlib.Path(jobs[0]["inputs"][1]["local"]).read_text())})
        out = pathlib.Path(jobs[0]["outputs"][0]["local"])
        frames(out / "full", names)
        frames(out / "check", names)
        stopped = {**RECORD, "failure": "SystemExit: the full pass made 0 frames of 8"}
        (out / "record.json").write_text(json.dumps(stopped if out.name == "stopped" else RECORD))
        return []

    monkeypatch.setitem(sys.modules, "cluster_jobs", types.SimpleNamespace(
        run=cluster_run, run_id=lambda kind: f"{kind}-run-1"))
    monkeypatch.setitem(sys.modules, "provider", types.SimpleNamespace(on_cluster=lambda kind: kind == "unreal"))
    monkeypatch.setattr(render, "ledger_rows", lambda run: [{"batch": run, "euros": 1.5}, {"batch": run, "euros": 1.5}])
    monkeypatch.setattr(render, "list_price", lambda card_class: pytest.fail("rows were there"))
    refused = project(tmp_path / "refused", GOOD + "[/Script/LinuxTargetPlatform.LinuxTargetSettings]\n"
                                                   "+TargetedRHIs=SF_VULKAN_SM5\n")

    def raised(call):
        try:
            call()
        except SystemExit as error:
            return str(error)
        return None

    job = render.job(good, 96, shot_file, tmp_path / "back")
    shot = render.shot(good / "Street.uproject", "/Game/Place/Street", "/Game/Place/Film.Film", 96)
    check_pass = shot["passes"][1]
    command = on_card.render_command(shot, check_pass)
    made = render.project_made(tmp_path / "made", "Score")
    (tmp_path / "engine/Plugins/Python/PythonScriptPlugin").mkdir(parents=True)
    (tmp_path / "engine/Plugins/Python/PythonScriptPlugin/PythonScriptPlugin.uplugin").write_text("{}")
    (tmp_path / "engine/Plugins/MovieScene/MovieRenderPipeline").mkdir(parents=True)
    (tmp_path / "engine/Plugins/MovieScene/MovieRenderPipeline/MovieRenderPipeline.uplugin").write_text("{}")
    dropped = on_card.plugins_held(made, tmp_path / "engine/Plugins")
    (tmp_path / "pkg").mkdir()
    scened = render.job(tmp_path / "made", 1, shot_file, tmp_path / "back", tmp_path / "pkg", tmp_path / "path.json")
    scene_shot = render.shot(made, "/m", "/s", 1, render.scene_step(tmp_path / "path.json"))
    (tmp_path / "failed/project/Saved/Logs").mkdir(parents=True)
    (tmp_path / "failed/project/Saved/Logs/Score.log").write_text("LogSpawn: Warning: SpawnActor failed\n")
    (tmp_path / "failed/out").mkdir()
    on_card.closed({"passes": {}}, "SystemExit: UnrealEditor-Cmd exited with 1", tmp_path / "failed/project/S.uproject",
                   tmp_path / "failed/out")
    (tmp_path / "stage").mkdir()
    (tmp_path / "stage/made.json").write_text(json.dumps({"faults": [{"what": "actor a"}]}))
    # (case, answer, expected), each expectation worked by hand
    rows = [
        ("a ray-tracing project passes", render.project_refusal(GOOD), None),
        ("SM5 still targeted is refused", render.project_refusal(
            GOOD + "[/Script/LinuxTargetPlatform.LinuxTargetSettings]\n+TargetedRHIs=SF_VULKAN_SM5\n"),
         "[/Script/LinuxTargetPlatform.LinuxTargetSettings] +TargetedRHIs=SF_VULKAN_SM5 must go (SM6 alone)"),
        ("no hardware ray tracing is refused",
         render.project_refusal(GOOD.replace("r.Lumen.HardwareRayTracing=True\n", "")),
         "[/Script/Engine.RendererSettings] r.Lumen.HardwareRayTracing=True is missing"),
        ("the cache name keeps through order, comments and other sections",
         render.ddc_name(REORDERED) == render.ddc_name(GOOD), True),
        ("a shader setting moves the cache", render.ddc_name(GOOD + "[/Script/Engine.RendererSettings]\n"
                                                                    "r.Shadow.Virtual.Enable=0\n") ==
         render.ddc_name(GOOD), False),
        ("another engine moves the cache", render.ddc_name(GOOD, engine="5.8.3") == render.ddc_name(GOOD), False),
        ("the cache name's head", render.ddc_name(GOOD).rsplit("-", 1)[0], "unreal-5.8.4-vulkan-sm6"),
        ("the job", {key: job[key] for key in ("minutes", "cards", "attempt_limit", "kernel_cache", "command")},
         {"minutes": 164, "cards": 1, "attempt_limit": 1, "kernel_cache": render.ddc_name(GOOD),
          "command": ["/opt/score/venv/bin/python", "tools/cloud/unreal/on_card.py", "/work/unreal/shot.json"]}),
        ("the job's project and out", (job["inputs"][0], job["outputs"]),
         ({"local": str(good), "path": "/work/unreal/project"},
          [{"path": "/work/unreal/out", "local": str(tmp_path / "back")}])),
        ("the passes", [(one["name"], one["start"], one["end"], one["folder"]) for one in shot["passes"]],
         [("full", 0, 96, "/work/unreal/out/full"), ("check", 0, 8, "/work/unreal/out/check")]),
        ("a short shot checks what it has", render.shot(good / "Street.uproject", "/m", "/s", 5)["passes"][1]["end"],
         5),
        ("the render command", command[:5] + [flag for flag in command if flag in ("-RenderOffscreen", "-Unattended",
                                                                                   "-nullrhi")],
         [render.EDITOR, "/work/unreal/project/Street.uproject", "/Game/Place/Street", "-game",
          "-LevelSequence=/Game/Place/Film.Film", "-RenderOffscreen", "-Unattended"]),
        ("the render command's config", "-MoviePipelineConfig=/Game/ScoreRender/Check.Check" in command, True),
        ("a made project can ray-trace", render.project_refusal((tmp_path / "made/Config/DefaultEngine.ini")
                                                                .read_text()), None),
        ("a made project's plugins the engine lacks", (dropped, [plugin["Name"] for plugin in json.loads(
            made.read_text())["Plugins"]]), (["EditorScriptingUtilities"],
                                             ["PythonScriptPlugin", "MovieRenderPipeline"])),
        ("a package goes up with its film path", (scened["code"], scened["inputs"][2:], scened["minutes"]),
         (["tools/cloud/unreal", "tools/unreal/scene"],
          [{"local": str(tmp_path / "pkg"), "path": "/work/unreal/package"},
           {"local": str(tmp_path / "path.json"), "path": "/work/unreal/path.json"}], 133)),
        ("the scene commandlet", [flag for flag in on_card.scene_command(scene_shot, "/r/editor.py")
                                  if flag.startswith("-script") or flag == "-nullrhi"],
         ["-script=/r/editor.py /work/unreal/package /work/unreal/stage /work/unreal/path.json", "-nullrhi"]),
        ("a failure comes back with the editor's logs", (
            (tmp_path / "failed/out/logs/Score.log").read_text(), render.card_failure(tmp_path / "failed/out")),
         ("LogSpawn: Warning: SpawnActor failed\n", "SystemExit: UnrealEditor-Cmd exited with 1")),
        ("a level made with faults goes on to render", on_card.scene_record(tmp_path / "stage", 1, 12.5),
         {"seconds": 12.5, "exit": 1, "made": {"faults": [{"what": "actor a"}]}}),
        ("no made.json, no level", raised(lambda: on_card.scene_record(tmp_path / "none", 0, 1.0)) is not None, True),
        ("the config commandlet has no GPU", [flag for flag in on_card.config_command(shot, "/x/in_editor.py")
                                              if flag in ("-nullrhi", "-run=pythonscript", "-script=/x/in_editor.py")],
         ["-run=pythonscript", "-script=/x/in_editor.py", "-nullrhi"]),
        ("vulkan without position fetch", on_card.vulkan_missing(VULKANINFO), ["VK_KHR_ray_tracing_position_fetch"]),
        ("vulkan's card", on_card.device_name(VULKANINFO), "NVIDIA L40S"),
        ("the image's driver on its node", on_card.driver_refusal("595.91.07", "595.91.07"), None),
        ("another node driver is refused naming both", on_card.driver_refusal("610.43.02", "595.91.07"),
         "the node's NVIDIA driver is 610.43.02, the image's graphics libraries are 595.91.07: rebuild the image for "
         "610.43.02 (NVIDIA_DRIVER in tools/cloud/images/unreal/Dockerfile)"),
        ("an image without a driver is refused", on_card.driver_refusal("595.91.07", None) is not None, True),
        ("vulkan with every extension passes", on_card.vulkan_refusal(
            VULKANINFO + "\tVK_KHR_ray_tracing_position_fetch : extension revision 1\n", "", 0), None),
        ("a failed vulkaninfo keeps its stderr's last lines", on_card.vulkan_refusal(
            "", "a\nERROR: [Loader Message] Code 0 : libGLX_nvidia.so.0: cannot open shared object file\n"
                "Cannot create Vulkan instance.\nb\nvkCreateInstance failed with ERROR_INCOMPATIBLE_DRIVER\n", 1),
         "vulkaninfo exited with 1; vulkaninfo said: ERROR: [Loader Message] Code 0 : libGLX_nvidia.so.0: cannot open "
         "shared object file | Cannot create Vulkan instance. | b | vkCreateInstance failed with "
         "ERROR_INCOMPATIBLE_DRIVER"),
        ("a killed cache server's cache is dropped", (on_card.cache_dropped(kept_cache(tmp_path / "killed"), False)
                                                     is not None, list((tmp_path / "killed").iterdir())), (True, [])),
        ("a stopped cache server's cache is kept", (on_card.cache_dropped(kept_cache(tmp_path / "stopped"), True),
                                                    len(list((tmp_path / "stopped").iterdir()))), (None, 2)),
        ("the cache beside CUDA's", on_card.ddc_folder({"CUDA_CACHE_PATH": "/cache/kernels/u/sm89-580.1/cuda"}),
         pathlib.Path("/cache/kernels/u/sm89-580.1/unreal-ddc")),
        ("no kernel cache, no render", raised(lambda: on_card.ddc_folder({})) is not None, True),
        ("the editor's cache variable", on_card.editor_environment({"A": "1"}, "/s.json", pathlib.Path("/d"), "/h"),
         {"A": "1", "HOME": "/h", "UE-LocalDataCachePath": "/d", "SCORE_UNREAL_SHOT": "/s.json"}),
        ("two clean renders are the same", {key: value for key, value in _twice.check(
            full, frames(tmp_path / "same", names), 8).items() if key in ("same", "faulty", "checked")},
         {"same": True, "faulty": [], "checked": 8}),
        ("a dark rectangle in one render", [(name, [fault["box"] for fault in found["faults"]]) for name, found in
                                            _twice.check(full, frames(tmp_path / "dark", names,
                                                                      {"0001.png": darkened}), 8)["frames"].items()],
         [("0001.png", [[64, 32, 32, 32], [96, 32, 32, 32], [64, 64, 32, 32], [96, 64, 32, 32]])]),
        ("a dark rectangle in the full render", _twice.check(frames(tmp_path / "full-dark", names, {
            "0002.png": darkened}), frames(tmp_path / "clean", names), 8)["faulty"], ["0002.png"]),
        ("a frame the check pass did not make", _twice.check(full, frames(tmp_path / "short", names[:7]), 8)["same"],
         False),
        ("a frame the full pass did not make", _twice.check(full, frames(tmp_path / "extra", ["0099.png"]), 1)["faulty"],
         ["0099.png"]),
        ("a frame priced from the run's rows", {key: value for key, value in _cost.frame_cost(
            RECORD, [{"euros": 1.5}, {"euros": 1.5}], "gpu-48gb").items()
            if key in ("euros", "euros_per_frame", "warm_pass_seconds_per_frame", "shader_cache")},
         {"euros": 3.0, "euros_per_frame": 0.03125, "warm_pass_seconds_per_frame": 10.0,
          "shader_cache": {"bytes_before": 0, "bytes_after": 5, "compiled": True}}),
        ("a queue run priced from its minutes", {key: value for key, value in _cost.frame_cost(
            RECORD, [], "gpu-48gb", 0.03).items() if key in ("euros", "euros_per_frame")},
         {"euros": 0.3, "euros_per_frame": 0.003125}),
        ("a refused project is never sent", (raised(lambda: render.render(
            refused, "/m", "/s", 96, "gpu-48gb", tmp_path / "r", "tester")) is not None, len(sent)), (True, 0)),
        ("an H100 is refused", raised(lambda: render.render(good, "/m", "/s", 96, "gpu-80gb", tmp_path / "h", "t"))
         is not None, True),
    ]
    run_name = render.render(good, "/Game/Place/Street", "/Game/Place/Film.Film", 8, "gpu-48gb", tmp_path / "back",
                             "tester")
    rows += [
        ("the run", (run_name, [(one["kind"], one["image"], one["classes"]) for one in sent]),
         ("unreal-run-1", [("unreal", "unreal", ["gpu-48gb"])])),
        ("the shot sent up", sent[0]["shot"]["passes"][1]["end"], 8),
        ("the scratch shot is gone", pathlib.Path(sent[0]["job"]["inputs"][1]["local"]).exists(), False),
        ("what was written back", (json.loads((tmp_path / "back/twice.json").read_text())["same"],
                                   json.loads((tmp_path / "back/cost.json").read_text())["euros_per_frame"]),
         (True, 0.03125)),
        ("a failure on the card fails the run", raised(lambda: render.render(
            good, "/m", "/s", 8, "gpu-48gb", tmp_path / "stopped", "t")),
         f"run unreal-run-1: the render stopped on the card: SystemExit: the full pass made 0 frames of 8 (the "
         f"editor's logs in {tmp_path / 'stopped/logs'}, record.json beside them)"),
    ]
    wrong = [(case, answer, expected) for case, answer, expected in rows if answer != expected]
    assert not wrong, wrong
