# tools/blender/

The Blender coding agents build scenes in (#128): our framework in Blender, as LEGO-Anything
(arXiv 2609.36380) drives it, so our scenes can be scored on LEGO-Bench. Bible chapter:
`workflow/bootstrap` (the runtime, `bash setup.sh`). Entry: `session.py`; its docstring has every
command.

- **No Blender window on the owner's screen, ever.** WSL shows every Linux window on the Windows
  desktop (WSLg: `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`); one Blender reached the owner's screen
  on 2026-10-05. Every Blender starts through `session.py`, which starts it through `launch.sh`:
  its own Xvfb on `:99` up, `DISPLAY` pointed there, a Wayland name with no socket behind it in an
  empty runtime folder, and the Xvfb stopped when Blender ends. A display under `:99` is refused by
  both (`session_test.py` checks it), and a started Blender found connected to WSLg's X0 or
  Wayland is stopped at once. Never run `blender` by hand, with `xvfb-run`, or from another
  script; a job that needs no window is `session.py batch` (`blender -b`).
- **Drawing is on the processor.** System Mesa's llvmpipe on the Xvfb screen and Cycles on the CPU.
  The graphics card is for game tests only. (Blender's own `blender-softwaregl` Mesa crashes in LLVM
  on this processor; do not switch to it.)
- **One Blender at a time on the machine**: the launch holds `flock` on
  `/tmp/farm-factory-blender.lock` for Blender's whole life. It starts only with 10 GB free (8 GB
  kept spare, `FARM_MIN_FREE_GB`), a watchdog ends it after 3 hours, and `stop` ends only the
  session `start` recorded. Stop it when you are done: `python3 tools/blender/session.py stop`.
- **How an agent drives it.** `session.py start`, then either the `blender` MCP server in
  `.mcp.json` (the add-on's own tools, `get_scene_info` and `execute_blender_code` among them) or
  `session.py run <file.py>` to run a file inside the same Blender. Both reach the add-on on
  127.0.0.1:9877 (not its 9876, which a Windows Blender may hold). The MCP server cannot start a
  Blender itself.
- **Telemetry stays off.** The add-on's consent is off (its default, set again at start) and
  `DISABLE_TELEMETRY=true` is set for Blender and the server, which otherwise sends an anonymous
  usage record. Its asset sources (Poly Haven, Sketchfab, Hyper3D, Hunyuan3D) stay off: no model or
  asset is fetched from outside our own tools.
- **LEGO's artifacts**: `session.py artifacts <folder>` (or `inside/artifacts.py` in a batch job)
  writes `scene.blend`, `scene.glb` and `final.png`, and refuses a scene with no active camera or
  no visible geometry, which their scorer marks invalid.
- **Versions**: 5.0.1 by default (LEGO's scorer; a newer `.blend` is not promised to open there),
  `--version 5.2.2` for the latest stable. `smoke.py` runs the whole route in seconds; it is not in
  the gate because it starts a Blender. `session_test.py` is, with the system python.
- Heavy model steps (Pixal3D, MoGe-2, SAM 3) stay in the cloud (`tools/props/cloud/`); nothing here
  loads a model.
