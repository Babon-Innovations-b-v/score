"""library-clips@<place> (place, paid): every item a place's handover made new gets a short preview clip, rendered in
cloud Blender with the films' renderer and light rig (tools/blender/inside/usd_views.py, Cycles on an L4 at the films'
size and samples), so what the cockpit shows is what ships (owner, 2026-10-20). It is a step of the items' handover in
their batch, never a re-render of the library as it stands: only the entries library@<place>'s report made new (status
other than unchanged or refused) and with no standing clip are rendered.

    make   the wanted entries from the handover report; the library's `clip-plan` says what each opens (its entries
           fetched into a work folder); each item's stage written with its sample shapes (sample.py: a surface on a
           ball, a sky or lamps over a sample room); one Blender job on one card (blender/render_clips.py, every item
           in turn on the one machine: no machine started per item), the frames back, each item's clip encoded here
           (ffmpeg, H.264 at the films' rate), then the library's `clip-attach` puts each clip into its draft entry
           and saves. The output: clips.json (per wanted entry: address, shelf, slug, why, planned), <slug>.mp4
           and <slug>.png (its first frame), attach.json (the library's report), plan.json (the library's plan).
    gate   clipped  every planned clip came back with FRAMES frames, its first frame not blank, attached and saved;
                    an entry with no clip to make (a sound, a locked one) is named, never a fault

Framing by shelf (blender/framing.py): a model, character, kit or surface turns round; an effect or a motion plays in
place; a sky or a place's lamps light a sample room the eye sweeps round. A sound has no clip; nor do an algorithm
(its demo), a place (its films) or the other layers.

The price (`per_item`, `forecast`): unmeasured until the first clips run, so estimated from the films' measured render
seconds a frame (ESTIMATED_FROM) at the L4's billed price, every frame once, with the one machine's set-up; the make
refuses (Blocked) a batch whose forecast high passes what its run was cleared at, a new ask at the forecast's price.
"""
import json
import pathlib
import shlex
import shutil
import subprocess

from PIL import Image, ImageStat

from score import checks, contracts, graph
from score.stages.demo_film import cleared_euros
from score.stages.library import backend, handover
from score.stages.library.clips import sample
from score.stages.library.clips.blender import framing

REPO = pathlib.Path(__file__).resolve().parents[4]
ROW, SAMPLE_ROW = "library-clips", "library-clips-sample"
SAMPLES = REPO / "data/definitions/clip_samples.json"  # {"why", "addresses"}: the clips' benchmark (SAMPLE_STAGE)
SCRIPT = "score/stages/library/clips/blender/render_clips.py"
FRAMER = "score/stages/library/clips/blender/framing.py"
DRAWER = "tools/blender/inside/usd_views.py"
CLASSES = "gpu-24gb"  # Cycles on the films' card (score/stages/demo_film CLASSES)
SIZE = (1280, 720)  # the films' (score/stages/demo_film SIZE)
NEW = ("new", "changed draft", "new version")  # a handover status of an entry made in this batch
# The price until clips are measured: the films' frames at 1280x720 on an L4 took 14 to 20 s each (tools/review/demo.py,
# the square and the hub, 2026-10-10); likely their middle, high their top.
FRAME_SECONDS = {"likely": 17.0, "high": 20.0}
ESTIMATED_FROM = ("estimated from the films' measured render seconds a frame (14 to 20 s at 1280x720 on an L4, "
                  "tools/review/demo.py, 2026-10-10) at the L4's billed EUR 0.7875 an hour; no clip measured yet")
CARD_EUROS_A_MINUTE = 0.7875 / 60  # the L4's bill (data/costs/per-unit.json light-passes' machine price, 2026-10-10)
OVERHEAD = 1.10  # time outside jobs on a warm card, the owner's target (per-unit.json's overhead, 2026-10-20)
SETUP_MINUTES = 8  # the one machine's set-up (tools/props/cloud/blender_cloud.py SETUP_MINUTES)
# An item's stage brought into Blender before its frames: not measured; a place's whole stage takes about 10 min
# (score/stages/demo_film JOB_LEAD_MINUTES), one item a small share of that.
ITEM_LEAD_MINUTES = 0.5
# The row's reservation while unmeasured: the most bought takes at one place in the remake's prepare record (the hub's
# 62, WORK/checks/prepare/remake.json, 2026-10-20), each a new model to clip.
PLACE_ITEMS = 62
SPREAD_LEAST = 4.0  # a first frame whose pixels spread less than this is blank (score/stages/demo_turntable's)
CLIPS, ATTACH, PLAN = "clips.json", "attach.json", "plan.json"


def per_item(seconds=FRAME_SECONDS):
    """{likely_euros, high_euros, frames, minutes, from} of one item's clip: its frames at the films' seconds a frame
    and its import, on the card's billed minute with the overhead."""
    found = {}
    for which in ("likely", "high"):
        minutes = framing.FRAMES * seconds[which] / 60 + ITEM_LEAD_MINUTES
        found[f"{which}_minutes"] = round(minutes, 2)
        found[f"{which}_euros"] = round(minutes * CARD_EUROS_A_MINUTE * OVERHEAD, 4)
    return {**found, "frames": framing.FRAMES, "from": ESTIMATED_FROM}


def forecast(items):
    """{items, frames, likely_euros, high_euros, high_minutes} of `items` clips on one machine: each item's price
    and the machine's set-up once (none for no items)."""
    if not items:
        return {"items": 0, "frames": 0, "likely_euros": 0.0, "high_euros": 0.0, "high_minutes": 0.0}
    one, setup = per_item(), SETUP_MINUTES * CARD_EUROS_A_MINUTE * OVERHEAD
    return {"items": items, "frames": items * one["frames"],
            "likely_euros": round(items * one["likely_euros"] + setup, 2),
            "high_euros": round(items * one["high_euros"] + setup, 2),
            "high_minutes": round(items * one["high_minutes"] + SETUP_MINUTES, 1)}


EUROS = forecast(PLACE_ITEMS)["high_euros"]


def wanted(report):
    """The addresses a handover report made new, sorted (module docstring)."""
    return sorted({row["address"] for row in report["entries"] if row["status"] in NEW and row["address"]})


def library_command(words):
    """(the library's command with `words`, its environment, the library's folder) from the library settings
    (backend.settings); Blocked with no library configured."""
    values = backend.settings()
    if backend.kind(values) == backend.NONE or not values.get("SCORE_LIB_ROOT"):
        raise graph.Blocked("no library configured: no entry to clip")
    command = shlex.split(values.get("SCORE_LIB_COMMAND") or backend.DEFAULT_COMMAND)
    environment = backend.command_environment(values, "", str(REPO))
    return [*command, "--root", values["SCORE_LIB_ROOT"], *words], environment, values["SCORE_LIB_ROOT"]


def run_library(words):
    """Run one library command; its output into the node's log. A non-zero exit raises RuntimeError."""
    command, environment, root = library_command(words)
    print("library:", shlex.join(command), flush=True)
    done = subprocess.run(command, env=environment, cwd=root, timeout=backend.TIMEOUT)
    if done.returncode:
        raise RuntimeError(f"the library's {words[0]} exited {done.returncode} (its words are in the log above)")


def slug_of(address):
    return address.replace("/", "-").replace("@", "-")


def refuse_over_clearance(planned, cleared):
    """Blocked before anything is bought when the forecast's high passes the euros the run was cleared at (`cleared`,
    None outside a cleared run): a dearer batch is a new ask at the forecast's price."""
    if cleared is not None and planned["high_euros"] > cleared + 1e-6:
        raise graph.Blocked(f"{planned['items']} clips: the forecast's high EUR {planned['high_euros']} passes the "
                            f"EUR {cleared:.2f} cleared; a new ask at the forecast's price")


def item_entry(row, folder):
    """One item of the Blender job's manifest: its stage written (sample.item_stage) and how it is framed."""
    stage = sample.item_stage(folder / slug_of(row["address"]), row)
    return {"slug": slug_of(row["address"]), "stage": str(stage), "framing": framing.FRAMING[row["shelf"]],
            "focus": row["focus"] or sample.focus(row["shelf"]), "start": row["start"] or 0.0, "end": row["end"] or 0.0,
            "per_second": row["per_second"] or framing.RATE}


def render(manifest, frames, minutes, log):
    """The one Blender job on one card (the runner's clearance names it); its log kept beside the output."""
    job = manifest.parent / "job.json"
    job.write_text(json.dumps({"script": SCRIPT, "args": [str(manifest), str(frames)],
                               "inputs": [str(manifest.parent)], "outputs": [str(frames)],
                               "minutes": round(minutes)}, indent=1))
    python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    done = subprocess.run([str(python), str(REPO / "tools/props/cloud/blender_cloud.py"), str(job),
                           "--who", ROW, "--classes", CLASSES], cwd=REPO, capture_output=True, text=True)
    log.write_text(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-2000:]}")


def encode(frames, film):
    """An item's frames into one H.264 film at the films' rate; '' or why not."""
    found = sorted(frames.glob("f*-look.png"))
    if len(found) != framing.FRAMES:
        return f"{len(found)} of {framing.FRAMES} frames came back"
    done = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(framing.RATE), "-i",
                           str(frames / "f%03d-look.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                           "-movflags", "+faststart", str(film)], capture_output=True, text=True)
    return "" if done.returncode == 0 else f"ffmpeg: {done.stderr.strip()[-300:]}"


def clip_rows(planned, frames, out, rendered):
    """[{address, shelf, slug, why}] of the planned items, each encoded into <slug>.mp4 and <slug>.png; why says
    what went wrong ('' when its clip is made)."""
    rows = []
    for row in planned:
        slug = slug_of(row["address"])
        why = (rendered.get(slug) or {}).get("why") or ("" if slug in rendered else "not rendered")
        if not why:
            why = encode(frames / slug, out / f"{slug}.mp4")
        if not why:
            shutil.copy(frames / slug / "f000-look.png", out / f"{slug}.png")
        rows.append({"address": row["address"], "shelf": row["shelf"], "slug": slug, "why": why})
    return rows


def attach(rows, out):
    """The made clips into their entries through the library's command; its report in attach.json."""
    made = [{"address": row["address"], "file": str(out / f"{row['slug']}.mp4"), "shelf": row["shelf"],
             "frames": framing.FRAMES, "seconds": framing.SECONDS, "size": list(SIZE), "made_by": ROW}
            for row in rows if not row["why"]]
    if not made:
        handover.write(out / ATTACH, {"attached": [], "refused": [], "saved": {"committed": None, "pushed": False,
                                                                                "why": "no clip made"}})
        return
    listing = out / ".attach-rows.json"
    listing.write_text(json.dumps(made, indent=1))
    try:
        run_library(["clip-attach", "--clips", str(listing), "--out", str(out / ATTACH),
                     "--message", f"clips: {len(made)} preview clips made at handover"])
    finally:
        listing.unlink()


def rendered_rows(planned, library, frames, out):
    """The planned items rendered in one job, encoded and put into their entries; their clip rows."""
    if not planned:
        return []
    refuse_over_clearance(forecast(len(planned)), cleared_euros())
    manifest = library / "manifest.json"
    items = [item_entry(row, library / "stages") for row in planned]
    manifest.write_text(json.dumps({"search": str(library), "size": list(SIZE), "items": items}, indent=1))
    render(manifest, frames, forecast(len(planned))["high_minutes"], out / "render.log")
    rows = clip_rows(planned, frames, out, json.loads((frames / "rendered.json").read_text()))
    attach(rows, out)
    return rows


def clipped(addresses, out):
    """The clips of `addresses` made into `out` (module docstring's make, from the library's plan on)."""
    if not addresses:
        handover.write(out / CLIPS, [])
        return
    work = out / ".work"
    try:
        run_library(["clip-plan", *addresses, "--into", str(work / "library")])
        plan = json.loads((work / "library" / "clip-plan.json").read_text())
        handover.write(out / PLAN, plan)
        rows = rendered_rows([row for row in plan if not row["why"]], work / "library", work / "frames", out)
        skipped = [{"address": row["address"], "shelf": row.get("shelf"), "slug": None, "why": row["why"],
                    "planned": False} for row in plan if row["why"]]
        handover.write(out / CLIPS, [{**row, "planned": True} for row in rows] + skipped)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def make(inputs, out, seed, params):
    """The clips of the items the place's handover made new (module docstring)."""
    clipped(wanted(handover.report(pathlib.Path(inputs["library"]))), out)


def make_samples(inputs, out, seed, params):
    """The clips of the sample record's entries (SAMPLES): the clips' benchmark."""
    clipped(json.loads(pathlib.Path(inputs["samples"]).read_text())["addresses"], out)


def output_faults(folder):
    return [] if (pathlib.Path(folder) / CLIPS).is_file() else [f"no {CLIPS}"]


CONTRACT = contracts.Contract(ROW, 1, output_faults)


def frame_count(film):
    """The frames ffprobe counts in a film, or None when it cannot read it."""
    done = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                           "stream=nb_read_frames", "-of", "csv=p=0", str(film)], capture_output=True, text=True)
    return int(done.stdout.strip()) if done.returncode == 0 and done.stdout.strip().isdigit() else None


def clip_faults(folder, row, attached):
    """Why one made clip is not a whole one in its entry, or [] when it is."""
    if row["why"]:
        return [f"{row['address']}: {row['why']}"]
    film, poster = folder / f"{row['slug']}.mp4", folder / f"{row['slug']}.png"
    faults = []
    counted = frame_count(film) if film.is_file() else None
    if counted != framing.FRAMES:
        faults.append(f"{row['address']}: {counted} of {framing.FRAMES} frames in its clip")
    if poster.is_file() and max(ImageStat.Stat(Image.open(poster).convert("RGB")).stddev) < SPREAD_LEAST:
        faults.append(f"{row['address']}: blank")
    if row["address"] not in attached:
        faults.append(f"{row['address']}: not in its entry")
    return faults


def judge_clipped(output, inputs, evidence):
    """Every planned clip whole, in its entry and saved (module docstring)."""
    folder = pathlib.Path(output)
    rows = [row for row in json.loads((folder / CLIPS).read_text()) if row["planned"]]
    report = json.loads((folder / ATTACH).read_text()) if (folder / ATTACH).is_file() else {}
    faults = [fault for row in rows for fault in clip_faults(folder, row, set(report.get("attached", [])))]
    if rows and not (report.get("saved") or {}).get("committed"):
        faults.append(f"the library did not save the clips: {(report.get('saved') or {}).get('why', 'no report')}")
    reason = "; ".join(faults[:3]) if faults else f"{len(rows)} clips made, in their entries and saved" if rows \
        else "no new item to clip"
    return checks.Verdict("clipped", checks.FAIL if faults else checks.PASS, reason,
                          {"clips": len(rows), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("clipped", judge_clipped),)


def files(place=None):
    """The Blender script, its framing and the drawer it runs: shipped to the machine, so declared."""
    return {"clip script": "{repo}/" + SCRIPT, "framing": "{repo}/" + FRAMER, "drawer": "{repo}/" + DRAWER}


STAGE = graph.Stage(ROW, "place", make, CONTRACT, CHECKS, files=files,
                    after={"library": (handover.SCHEMA, handover.VERSION)}, paid=True, euros=EUROS)


def sample_addresses():
    """The sample record's addresses (none without it)."""
    return json.loads(SAMPLES.read_text())["addresses"] if SAMPLES.is_file() else []


# The benchmark (environment data, SAMPLES): a few library drafts of different shelves clipped by the same make, so
# a clip's seconds and euros are measured before a batch relies on the estimate. One environment node, paid.
SAMPLE_STAGE = graph.Stage(SAMPLE_ROW, "world", make_samples, CONTRACT, CHECKS,
                           files=lambda place=None: {"samples": "{data}/definitions/clip_samples.json", **files()},
                           paid=True, euros=forecast(len(sample_addresses()))["high_euros"])
