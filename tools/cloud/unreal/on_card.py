"""On the card, inside the score-unreal image (render.py's job): render one shot with Unreal Engine's Movie Render
Queue, headless, and write what it took. The job runtime runs this as root with the project and shot.json in place
and the shader cache restored (its kernel cache); this runs the editor as Epic's image's user, since Unreal refuses
root.

    /opt/score/venv/bin/python tools/cloud/unreal/on_card.py /work/unreal/shot.json

Steps, each failing the job loudly:
1. Vulkan with hardware ray tracing (`vulkaninfo`): a card or driver without it fails here, in seconds, not after a
   shader compile of an hour.
2. The config assets: one editor start as a commandlet (`-run=pythonscript`, no GPU) runs in_editor.py, which makes
   each pass's Movie Render Queue config from shot.json's recipe.
3. The full pass, then the check pass (the first frames again, a second editor process), each
   `UnrealEditor-Cmd <project> <map> -game -LevelSequence=... -MoviePipelineConfig=... -RenderOffscreen -Unattended`.
4. Unreal's local cache server (zenserver), which outlives the editor, is stopped, so the runtime packs a cache no
   process is writing (its kernel cache upload follows the command).

The Derived Data Cache goes into the job's kernel-cache folder (the parent of the CUDA cache the runtime points
there) through `UE-LocalDataCachePath`, a variable a shell cannot set (its name has a dash), set here. record.json in
the out folder holds each step's seconds, each pass's frames, the card Vulkan named and the cache's bytes before and
after.
"""
import json
import os
import pathlib
import pwd
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
# What Lumen's hardware ray tracing and Nanite ask of the Vulkan driver (#216; position fetch since UE 5.5).
EXTENSIONS = ("VK_KHR_ray_tracing_pipeline", "VK_KHR_ray_query", "VK_KHR_acceleration_structure",
              "VK_KHR_ray_tracing_position_fetch", "VK_KHR_shader_atomic_int64")
DDC_FOLDER = "unreal-ddc"
ZEN = "zenserver"
ZEN_SECONDS = 60


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


def editor_environment(environ, shot_path, ddc, home):
    """The editor's environment: the job's, its user's home, the cache's folder and where in_editor.py finds the
    shot."""
    return {**environ, "HOME": home, "UE-LocalDataCachePath": str(ddc), "SCORE_UNREAL_SHOT": str(shot_path)}


def config_command(shot, script):
    """The commandlet that makes the passes' config assets (no GPU: -nullrhi)."""
    return [shot["editor"], shot["project"], "-run=pythonscript", f"-script={script}", "-nullrhi", "-Unattended",
            "-NoSplash", "-NoSound", "-stdout", "-FullStdOutLogOutput"]


def render_command(shot, one_pass):
    """The headless Movie Render Queue render of one pass: the GPU on, no window (-RenderOffscreen), no prompts."""
    recipe = shot["recipe"]
    return [shot["editor"], shot["project"], shot["map"], "-game", f"-LevelSequence={shot['sequence']}",
            f"-MoviePipelineConfig={one_pass['config']}", "-RenderOffscreen", "-Unattended", "-NoSplash", "-NoSound",
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


def run_as(command, user, environ):
    """Run the command as `user`; its seconds. A non-zero exit fails the job."""
    began = time.time()
    done = subprocess.run(command, user=user, group=pwd.getpwnam(user).pw_gid, extra_groups=[], env=environ)
    if done.returncode:
        raise SystemExit(f"{pathlib.Path(command[0]).name} exited with {done.returncode}: {command[2:5]}")
    return round(time.time() - began, 1)


def zen_pids():
    """The processes named ZEN in this container."""
    found = []
    for comm in pathlib.Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text().strip() == ZEN:
                found.append(int(comm.parent.name))
        except OSError:
            continue  # gone while read
    return found


def stop_zen():
    """End the cache server the editor left, waiting up to ZEN_SECONDS; it is the job's own (one pod, one job)."""
    for pid in zen_pids():
        os.kill(pid, signal.SIGTERM)
    deadline = time.time() + ZEN_SECONDS
    while zen_pids() and time.time() < deadline:
        time.sleep(1)
    if zen_pids():
        raise SystemExit(f"{ZEN} did not stop within {ZEN_SECONDS} s; the shader cache would be packed mid-write")


def main(shot_path):
    began = time.time()
    shot = json.loads(pathlib.Path(shot_path).read_text())
    vulkaninfo = subprocess.run(["vulkaninfo"], capture_output=True, text=True).stdout
    missing = vulkan_missing(vulkaninfo)
    if missing:
        raise SystemExit(f"Vulkan lacks {', '.join(missing)}: no hardware ray tracing on this card or driver")
    ddc, user = ddc_folder(os.environ), shot["user"]
    out = pathlib.Path(shot["out"])
    for folder in (ddc, out, pathlib.Path(shot["project"]).parent):
        give(folder, user)
    environ = editor_environment(os.environ, shot_path, ddc, pwd.getpwnam(user).pw_dir)
    record = {"card": device_name(vulkaninfo), "ddc": {"folder": str(ddc), "bytes_before": size_of(ddc)},
              "passes": {"config": {"seconds": run_as(config_command(shot, HERE / "in_editor.py"), user, environ)}}}
    for one_pass in shot["passes"]:
        seconds = run_as(render_command(shot, one_pass), user, environ)
        frames = len(list(pathlib.Path(one_pass["folder"]).glob("*.png")))
        if frames != one_pass["end"] - one_pass["start"]:
            raise SystemExit(f"the {one_pass['name']} pass made {frames} frames of "
                             f"{one_pass['end'] - one_pass['start']}")
        record["passes"][one_pass["name"]] = {"seconds": seconds, "frames": frames}
    stop_zen()
    record["ddc"]["bytes_after"] = size_of(ddc)
    record["job_seconds"] = round(time.time() - began, 1)
    (out / "record.json").write_text(json.dumps(record, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
