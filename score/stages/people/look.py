"""The people's look rows: `people-look-<look>` (paid, environment, one a full look) render the dressed look it reads
(blender_shots.py on a rented card through blender_cloud.py: the bind pose from the front, side and back, and a strip
of clip frames) and write its review page, page.html, with its body gates' table (the body row's checks.txt) and its
dress.

Gate: `rendered` (every look came back with every view).
"""
import base64
import io
import json
import pathlib
import shutil
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
# The A-pose views and the shots of the clips the bodies are made with (people_bodies/made_clips.CLIPS: walking,
# sitting, the bench work); blender_shots.py skips a shot whose clip a body lacks.
VIEWS = ("apose_front", "apose_side", "apose_back", "walk_a", "walk_b", "sit", "work")
# A card render of eleven views at 768 px, 64 samples: about 6 minutes a look with the import (blender_shots.py on
# 2026-10-10 took about 3 minutes for five).
MINUTES = 12
EUROS = 1.5
ROW = "people-look"  # each look's row is `people-look-<look>`, its output's contract this schema


def dressed(inputs):
    """{look: its dress output folder}."""
    return {name[len("people-dress-"):]: pathlib.Path(path) for name, path in inputs.items()
            if name.startswith("people-dress-")}


def make_look(inputs, out, seed, params):
    jobs = []
    scratch = out / ".jobs"
    scratch.mkdir(parents=True)
    for look, folder in dressed(inputs).items():
        outfit = json.loads((folder / "look.json").read_text())["outfit"]
        shots = out / "shots" / look
        shots.mkdir(parents=True)
        job = scratch / f"{look}.json"
        job.write_text(json.dumps({"script": "tools/characters/maker/blender_shots.py",
                                   "args": [str(folder / "body.glb"), str(shots), "--outfit", outfit],
                                   "inputs": [str(folder / "body.glb")], "outputs": [str(shots)],
                                   "minutes": MINUTES}, indent=1))
        jobs.append(job)
    done = subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), *map(str, jobs),
                           "--who", "people-look", "--classes", "gpu-24gb"], cwd=REPO, capture_output=True, text=True)
    (out / "look.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-3000:]}")
    shutil.rmtree(scratch)
    (out / "page.html").write_text(page(inputs, out))


def picture(path):
    """A render as a JPEG data URI (the page stays one file)."""
    from PIL import Image
    image = Image.open(path).convert("RGB")
    held = io.BytesIO()
    image.save(held, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(held.getvalue()).decode()


def page(inputs, out):
    """The review page: per look, its views, its gates' table and its dress."""
    sections = []
    for look, folder in dressed(inputs).items():
        body = pathlib.Path(inputs[f"people-body-{look}"])
        table = (body / "checks" / "checks.txt").read_text() if (body / "checks" / "checks.txt").exists() else ""
        dress = json.loads((folder / "dress.json").read_text())["surfaces"]
        worn = sorted({entry["library"] for entry in dress.values() if entry.get("library")})
        views = "".join(f'<figure><img src="{picture(out / "shots" / look / f"{view}.png")}" alt="{look} {view}">'
                        f"<figcaption>{view.replace('_', ' ')}</figcaption></figure>"
                        for view in VIEWS if (out / "shots" / look / f"{view}.png").exists())
        sections.append(f"<section><h2>{look}</h2><div class=strip>{views}</div>"
                        f"<p>Library surfaces worn: {', '.join(worn)}</p><pre>{table}</pre></section>")
    return ("<title>People review</title><style>:root{--bg:#fff;--fg:#1d1d1f;--mute:#666}"
            "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#161618;--fg:#eee;--mute:#aaa;"
            "color-scheme:dark}}:root[data-theme=dark]{--bg:#161618;--fg:#eee;--mute:#aaa;color-scheme:dark}"
            "body{background:var(--bg);color:var(--fg);padding:16px;font:14px system-ui}"
            ".strip{display:flex;flex-wrap:wrap;gap:8px}figure{margin:0;width:min(220px,45%)}"
            "img{width:100%;border-radius:4px}figcaption{color:var(--mute);font-size:12px}"
            "pre{overflow-x:auto;font-size:11px}</style>"
            "<h1>People on the prop route</h1><p>Each look's body as built, put through the people route and dressed "
            "with library "
            "surfaces, its gates measured by the people stage (#5).</p>" + "".join(sections))


def look_faults(folder):
    return [] if (folder / "page.html").exists() else ["no page.html"]


def judge_rendered(output, inputs, evidence):
    from score.checks import FAIL, PASS, Verdict
    missing = [f"{look}: {view}" for look in dressed(inputs) for view in VIEWS
               if not (output / "shots" / look / f"{view}.png").exists()]
    return Verdict("rendered", FAIL if missing else PASS, "; ".join(missing[:8]) or "every look, every view",
                   {"failing": len(missing)}, {"failing": "lower"}, tuple(missing))
