"""On the card, inside the score-unreal image (render.py's job): render one shot with Unreal Engine's Movie Render
Queue, headless, and write what it took. The job runtime runs this as root with the project and shot.json in place
and the shader cache restored (its kernel cache); this runs the editor as Epic's image's user, since Unreal refuses
root.

    /opt/score/venv/bin/python tools/cloud/unreal/on_card.py /work/unreal/shot.json

Steps, each failing the job loudly:
1. Vulkan with hardware ray tracing (`vulkaninfo`): a card or driver without it fails here, in seconds, not after a
   shader compile of an hour. First the node's driver (`nvidia-smi`) is held against the one the image carries the
   graphics libraries of (SCORE_NVIDIA_DRIVER, the Dockerfile's NVIDIA_DRIVER): user libraries of another version
   than the kernel module do not load. A failing vulkaninfo's last stderr lines go into the failure.
2. The level, when the shot has a scene step (render.py --package): a commandlet (`-run=pythonscript`, no GPU) runs
   tools/unreal/scene/editor.py, which makes the level and its Level Sequence from the scene package; its made.json
   (written last, so a script that raised leaves none, whatever the commandlet's exit) is checked and recorded.
   The project's plugins the image does not hold are dropped from its .uproject first, and named in record.json.
3. The config assets: one editor start as a commandlet (`-run=pythonscript`, no GPU) runs in_editor.py, which makes
   each pass's Movie Render Queue config from shot.json's recipe.
4. The full pass, then the check pass (the first frames again, a second editor process), each
   `UnrealEditor-Cmd <project> <map> -game -LevelSequence=... -MoviePipelineConfig=... -RenderOffscreen -Unattended`.
5. Unreal's local cache server (zenserver), which outlives the editor, is stopped, so the runtime packs a cache no
   process is writing (its kernel cache upload follows the command). A server that ended is a zombie until reaped
   (the job's first process reaps no orphans), so a zombie counts as stopped (zen_pids).

The Derived Data Cache goes into the job's kernel-cache folder (the parent of the CUDA cache the runtime points
there): UE 5.8 keeps it in its user's home whatever `UE-LocalDataCachePath` says (#222, run 8: zenserver's data
and the filesystem cache under ~/.config/Epic/UnrealEngine/Common, the kernel-cache folder left empty), so those
folders are links into it (caches_linked) before the editor first starts. record.json in
the out folder holds each step's seconds, each pass's frames, the card Vulkan named and the cache's bytes before and
after; logs/ the editor's own logs of every start. A failing step still writes record.json (its `failure`) and
logs/, and the job exits 0 so the runtime brings them back (it brings outputs back only from a command that
succeeded); render.py fails the run on that failure.
"""
import json
import os
import pathlib
import pwd
import shutil
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
# What Lumen's hardware ray tracing and Nanite ask of the Vulkan driver (#216; position fetch since UE 5.5).
EXTENSIONS = ("VK_KHR_ray_tracing_pipeline", "VK_KHR_ray_query", "VK_KHR_acceleration_structure",
              "VK_KHR_ray_tracing_position_fetch", "VK_KHR_shader_atomic_int64")
DDC_FOLDER = "unreal-ddc"
ZEN = "zenserver"
ZEN_SECONDS = 60
# The editor's caches in its user's home (UE 5.8 on Linux), each linked to a folder of that name in the shader cache.
CACHE_HOMES = {"zen": ".config/Epic/UnrealEngine/Common/Zen/Data",
               "local": ".config/Epic/UnrealEngine/Common/DerivedDataCache"}
STDERR_LINES = 4


def driver_refusal(node, baked):
    """Why the node's driver cannot run the image's graphics libraries (None when it can): `node` as nvidia-smi gives
    it, `baked` the image's SCORE_NVIDIA_DRIVER."""
    if not baked:
        return "the image names no SCORE_NVIDIA_DRIVER: it carries no graphics libraries for a known driver"
    if node != baked:
        return (f"the node's NVIDIA driver is {node or 'unknown'}, the image's graphics libraries are {baked}: "
                f"rebuild the image for {node or 'the node'} (NVIDIA_DRIVER in tools/cloud/images/unreal/Dockerfile)")
    return None


def node_driver():
    """The node's driver version as nvidia-smi gives it, or '' when it gives none."""
    done = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], capture_output=True,
                          text=True)
    lines = done.stdout.split()
    return lines[0] if lines else ""


def vulkan_refusal(stdout, stderr, returncode):
    """Why `vulkaninfo`'s run shows no hardware ray tracing (None when it does), its stderr's last lines kept."""
    missing = vulkan_missing(stdout)
    if not returncode and not missing:
        return None
    tail = " | ".join(line.strip() for line in stderr.strip().splitlines()[-STDERR_LINES:])
    head = (f"vulkaninfo exited with {returncode}" if returncode
            else f"Vulkan lacks {', '.join(missing)}: no hardware ray tracing on this card or driver")
    return f"{head}; vulkaninfo said: {tail}" if tail else head


def vulkan_missing(vulkaninfo):
    """The extensions EXTENSIONS names that `vulkaninfo`'s output does not list."""
    return [name for name in EXTENSIONS if name not in vulkaninfo]


def device_name(vulkaninfo):
    """The first device name `vulkaninfo` gives, or None."""
    for line in vulkaninfo.splitlines():
        if line.strip().startswith("deviceName"):
            return line.split("=", 1)[-1].strip()
    return None


def ddc_folder(environ):
    """The shader cache's folder: in the job's kernel-cache folder, beside the CUDA cache the runtime points there."""
    if not environ.get("CUDA_CACHE_PATH"):
        raise SystemExit("no kernel cache: the job must name render.ddc_name as its kernel_cache")
    return pathlib.Path(environ["CUDA_CACHE_PATH"]).parent / DDC_FOLDER


def editor_environment(environ, shot_path, home):
    """The editor's environment: the job's, its user's home and where in_editor.py finds the shot."""
    return {**environ, "HOME": home, "SCORE_UNREAL_SHOT": str(shot_path)}


def caches_linked(home, ddc):
    """Each of the editor's home caches (CACHE_HOMES) a link to its folder in the shader cache `ddc`, so what the
    editor writes there is packed with the job (a folder already there, the pod's own, is replaced); the links."""
    links = []
    for name, inside in CACHE_HOMES.items():
        (ddc / name).mkdir(parents=True, exist_ok=True)
        link = pathlib.Path(home) / inside
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.is_dir():
            shutil.rmtree(link)
        link.symlink_to(ddc / name, target_is_directory=True)
        links.append(link)
    return links


def config_command(shot, script):
    """The commandlet that makes the passes' config assets (no GPU: -nullrhi)."""
    return [shot["editor"], shot["project"], "-run=pythonscript", f"-script={script}", "-nullrhi", "-Unattended",
            "-NoSplash", "-NoSound", "-stdout", "-FullStdOutLogOutput"]


def scene_command(shot, script):
    """The commandlet that makes the level from the scene package (no GPU: -nullrhi); its arguments ride in -script,
    as the Python plugin's commandlet takes them."""
    scene = shot["scene"]
    words = [str(script), scene["package"], scene["into"]] + ([scene["path"]] if scene["path"] else [])
    return [shot["editor"], shot["project"], "-run=pythonscript", f"-script={' '.join(words)}", "-nullrhi",
            "-Unattended", "-NoSplash", "-NoSound", "-stdout", "-FullStdOutLogOutput"]


def object_path(asset_path):
    """An asset's object path as the command line names it: /Game/A/B as /Game/A/B.B (kept when it has one)."""
    name = asset_path.rsplit("/", 1)[-1]
    return asset_path if "." in name else f"{asset_path}.{name}"


def plugins_held(project_file, engine_plugins):
    """The project's .uproject keeping only the plugins the engine holds (a .uplugin of that name under
    `engine_plugins`); the names dropped. An editor started on a project naming a missing plugin stops."""
    project = json.loads(pathlib.Path(project_file).read_text())
    held = {path.stem for path in pathlib.Path(engine_plugins).rglob("*.uplugin")}
    dropped = [plugin["Name"] for plugin in project.get("Plugins", []) if plugin["Name"] not in held]
    if dropped:
        project["Plugins"] = [plugin for plugin in project["Plugins"] if plugin["Name"] in held]
        pathlib.Path(project_file).write_text(json.dumps(project, indent=1))
    return dropped


def render_command(shot, one_pass):
    """The headless Movie Render Queue render of one pass: the GPU on, no window (-RenderOffscreen), no prompts."""
    recipe = shot["recipe"]
    return [shot["editor"], shot["project"], shot["map"], "-game", f"-LevelSequence={shot['sequence']}",
            f"-MoviePipelineConfig={object_path(one_pass['config'])}", "-RenderOffscreen", "-Unattended", "-NoSplash",
            "-NoSound",
            "-vulkan", f"-ResX={recipe['width']}", f"-ResY={recipe['height']}", "-notexturestreaming", "-log",
            "-stdout", "-FullStdOutLogOutput"]


def size_of(folder):
    return sum(path.stat().st_size for path in folder.rglob("*") if path.is_file()) if folder.exists() else 0


def give(folder, user):
    """`folder` and everything in it to `user` (the runtime wrote them as root)."""
    entry = pwd.getpwnam(user)
    folder.mkdir(parents=True, exist_ok=True)
    os.chown(folder, entry.pw_uid, entry.pw_gid)
    for path in folder.rglob("*"):
        os.chown(path, entry.pw_uid, entry.pw_gid, follow_symlinks=False)


def exited(command, user, environ):
    """Run the command as `user`; its exit code and seconds."""
    began = time.time()
    done = subprocess.run(command, user=user, group=pwd.getpwnam(user).pw_gid, extra_groups=[], env=environ)
    return done.returncode, round(time.time() - began, 1)


def run_as(command, user, environ):
    """Run the command as `user`; its seconds. A non-zero exit fails the job."""
    returncode, seconds = exited(command, user, environ)
    if returncode:
        raise SystemExit(f"{pathlib.Path(command[0]).name} exited with {returncode}: {command[2:5]}")
    return seconds


def zen_pids(proc=pathlib.Path("/proc")):
    """The running processes named ZEN in this container. A zombie (state Z: it has ended, its parent has not
    reaped it) is not one: the job's first process reaps no orphans, so a server that stopped stays listed until
    the pod ends, and run 7 and 8 (#222) read that as a server that would not stop."""
    found = []
    for stat in pathlib.Path(proc).glob("[0-9]*/stat"):
        try:
            name, rest = stat.read_text().split("(", 1)[1].rsplit(")", 1)
        except (OSError, IndexError, ValueError):
            continue  # gone while read
        if name == ZEN and rest.split()[0] != "Z":
            found.append(int(stat.parent.name))
    return sorted(found)


def stop_zen():
    """End the cache server the editor left, waiting up to ZEN_SECONDS, then killing it; True when it stopped of
    itself. It is the job's own (one pod, one job)."""
    for pid in zen_pids():
        os.kill(pid, signal.SIGTERM)
    deadline = time.time() + ZEN_SECONDS
    while zen_pids() and time.time() < deadline:
        time.sleep(1)
    if not zen_pids():
        return True
    for pid in zen_pids():
        os.kill(pid, signal.SIGKILL)
    return False


def cache_dropped(ddc, stopped):
    """The shader cache emptied when its server had to be killed (it may hold a half-written file, so it is never
    packed); the reason, or None when the server stopped of itself. The frames are kept either way (#222, run 7)."""
    if stopped:
        return None
    for entry in pathlib.Path(ddc).iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    return f"{ZEN} did not stop within {ZEN_SECONDS} s and was killed; this run's shader cache was dropped"


def logs_kept(project_file, out):
    """The editor's own logs of every start (Saved/Logs) copied into <out>/logs."""
    logs = pathlib.Path(project_file).parent / "Saved/Logs"
    if logs.is_dir():
        shutil.copytree(logs, out / "logs", dirs_exist_ok=True)


def scene_made(shot, user, environ):
    """The scene step: the level made from the package by editor.py, its made.json read back (scene_record)."""
    into = pathlib.Path(shot["scene"]["into"])
    for folder in (into, pathlib.Path(shot["scene"]["package"])):
        give(folder, user)
    return scene_record(into, *exited(scene_command(shot, REPO / shot["scene"]["script"]), user, environ))


def scene_record(into, returncode, seconds):
    """The scene step's record {seconds, exit, made} from <into>/made.json, which editor.py writes last: its faults
    were logged as errors, so the commandlet exits non-zero with a level made, and made.json, not the exit code, says
    the level stands. Refused when there is none."""
    if not (into / "made.json").is_file():
        raise SystemExit(f"editor.py wrote no made.json (the commandlet exited with {returncode}): the level was not "
                         "made (the editor's log in logs/ says where it stopped)")
    return {"seconds": seconds, "exit": returncode, "made": json.loads((into / "made.json").read_text())}


def closed(record, failure, project_file, out):
    """The job's end, whether its steps finished or `failure` (a step's error, or None) stopped them: the editor's
    logs kept and <out>/record.json written with the failure. The job then exits 0 even on a failure, since the
    runtime brings the out folder back only from a command that succeeded; render.py reads the failure from
    record.json (render.card_failure) and fails the run there. (main stops the cache server first: one that does
    not stop is killed and its cache dropped, so no cache is packed mid-write and the frames still come back.)"""
    logs_kept(project_file, out)
    record["failure"] = failure
    (out / "record.json").write_text(json.dumps(record, indent=1))


def main(shot_path):
    began = time.time()
    shot = json.loads(pathlib.Path(shot_path).read_text())
    refusal = driver_refusal(node_driver(), os.environ.get("SCORE_NVIDIA_DRIVER"))
    if refusal:
        raise SystemExit(refusal)
    done = subprocess.run(["vulkaninfo"], capture_output=True, text=True)
    refusal = vulkan_refusal(done.stdout, done.stderr, done.returncode)
    if refusal:
        raise SystemExit(refusal)
    vulkaninfo = done.stdout
    ddc, user = ddc_folder(os.environ), shot["user"]
    out = pathlib.Path(shot["out"])
    home = pwd.getpwnam(user).pw_dir
    caches_linked(home, ddc)
    for folder in (ddc, out, pathlib.Path(shot["project"]).parent, pathlib.Path(home) / ".config"):
        give(folder, user)
    environ = editor_environment(os.environ, shot_path, home)
    engine_plugins = pathlib.Path(shot["editor"]).parents[2] / "Plugins"  # <engine>/Engine/Plugins
    record = {"card": device_name(vulkaninfo), "ddc": {"folder": str(ddc), "bytes_before": size_of(ddc)},
              "plugins_dropped": plugins_held(shot["project"], engine_plugins), "passes": {}}
    try:
        passes_run(shot, user, environ, record)
        failure = None
    except (Exception, SystemExit) as error:  # noqa: BLE001 - written to record.json; render.py fails the run on it
        failure = f"{type(error).__name__}: {error}"
    record["ddc"]["dropped"] = cache_dropped(ddc, stop_zen())
    record["ddc"]["bytes_after"] = size_of(ddc)
    record["job_seconds"] = round(time.time() - began, 1)
    closed(record, failure, shot["project"], out)


def passes_run(shot, user, environ, record):
    """The scene step (with a package), the config assets and every pass, each one's seconds (and frames) put in
    record["passes"] as it ends; the first that fails raises."""
    if shot.get("scene"):
        record["passes"]["scene"] = scene_made(shot, user, environ)
    record["passes"]["config"] = {"seconds": run_as(config_command(shot, HERE / "in_editor.py"), user, environ)}
    for one_pass in shot["passes"]:
        seconds = run_as(render_command(shot, one_pass), user, environ)
        frames = len(list(pathlib.Path(one_pass["folder"]).glob("*.png")))
        if frames != one_pass["end"] - one_pass["start"]:
            raise SystemExit(f"the {one_pass['name']} pass made {frames} frames of "
                             f"{one_pass['end'] - one_pass['start']}")
        record["passes"][one_pass["name"]] = {"seconds": seconds, "frames": frames}


if __name__ == "__main__":
    main(sys.argv[1])
