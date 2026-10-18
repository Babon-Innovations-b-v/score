"""Every vendored tool in vendor/ and where the framework calls it, so a tool is never vendored and forgotten.

    vendored.TOOLS["kimodo"]   # {"use", "callers", "image", "stages", "why"}
    vendored.faults()          # why the table and vendor/ disagree, [] when they agree

`use` is one of:

    wired       called by the framework: `callers` are the repository files that call it (each names the tool),
                `image` the cloud image kind that carries it (tools/cloud/images, pinned by the models adapter) or
                None when it runs in Blender or on the processor, `stages` the stage packages that reach it
    agent tool  an agent's tool (memory, code graph, lean-code rules), wired in .claude/, never by a stage
    left out    vendored but not called, `why` says why in plain words (an owner's decision, or what replaced it)

The table is checked, not trusted: `faults` refuses a vendor/ folder the table lacks, a row whose folder is gone, a
caller file that is missing or never names its tool, an image kind with no folder in tools/cloud/images and a stage
package that is not there. A new tool is wired the house way (bible `architecture/components`): a cloud runner in
tools/props/cloud with its image and pinned models, an adapter call where a stage keys on it, a test with a stand-in,
a rule in its caller's overlay; then its row here.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
WIRED, AGENT, LEFT_OUT = "wired", "agent tool", "left out"

TOOLS = {
    "image-to-3dlab": {
        "use": WIRED, "image": "pixal", "names": ("image-to-3dlab",),
        "callers": ("tools/props/pixal.py", "tools/props/paths.py", "tools/props/cloud/batch.py",
                    "tools/cloud/images/pixal/Dockerfile"),
        "stages": ("props", "crops", "people_takes"),
        "why": "Pixal3D, the model made from a picture (asset route locked 2026-09-28), always through pixal.py"},
    "infinigen2": {
        "use": WIRED, "image": None, "names": ("infinigen2",),
        "callers": ("tools/props/library/recipes.py", "tools/props/library/inside/runtime.py",
                    "tools/props/cloud/library_bake.py"),
        "stages": ("surfaces", "late_bake", "ship_kits"),
        "why": "its shader recipes (paint, brushed metal, rubber) under the ProcFunc library surfaces, baked in "
               "Blender on a rented card"},
    "procfunc": {
        "use": WIRED, "image": None, "names": ("procfunc", "ProcFunc"),
        "callers": ("tools/props/library/recipes.py", "tools/props/library/inside/runtime.py",
                    "tools/props/cloud/library_bake.py"),
        "stages": ("surfaces", "late_bake", "ship_kits"),
        "why": "the library surfaces' recipes, composable shader functions (owner, 2026-10-06)"},
    "kimodo": {
        "use": WIRED, "image": "characters-motion", "names": ("kimodo", "Kimodo"),
        "callers": ("tools/props/cloud/characters.py", "tools/characters/maker/chain.py",
                    "tools/characters/people/clips.py", "tools/cloud/images/characters-motion/Dockerfile"),
        "stages": ("people_bodies",),
        "why": "every person's and animal's motion clips, on the characters-motion image"},
    "sam3dbody-cpp": {
        "use": WIRED, "image": "characters-motion", "names": ("sam3dbody-cpp",),
        "callers": ("tools/characters/maker/body_picture.py", "tools/props/cloud/characters.py",
                    "tools/cloud/images/characters-motion/Dockerfile"),
        "stages": (),
        "why": "the character maker's body read off its A-pose picture (make.py, on rented cards); no stage keys on "
               "it: the people stages take the prop route's Pixal3D bodies (tools/characters/maker overlay)"},
    "sam-3d-body": {
        "use": LEFT_OUT, "image": None, "names": (), "callers": (), "stages": (),
        "why": "Meta's original Python release, kept for its licence and as the reference of sam3dbody-cpp, which "
               "runs its converted weights (characters-motion models.json) without its Python and torch stack"},
    "infinigen": {
        "use": LEFT_OUT, "image": None, "names": (), "callers": (), "stages": (),
        "why": "its nature patch runner was retired on 2026-10-06, when Pixal3D's nature props won the comparison; "
               "only its idea of annotations from one Blender render lives on (tools/blender/inside/"
               "annotate_stage.py, written fresh) and its processor-stock helper (tools/props/cloud/infinigen.py)"},
    "claude-mem": {"use": AGENT, "image": None, "names": (), "callers": (), "stages": (),
                   "why": "cross-session memory of agents (root CLAUDE.md, Agent tools), switched off"},
    "codebase-memory-mcp": {"use": AGENT, "image": None, "names": (), "callers": (), "stages": (),
                            "why": "the code graph agents search (root CLAUDE.md, Agent tools)"},
    "ponytail": {"use": AGENT, "image": None, "names": (), "callers": (), "stages": (),
                 "why": "lean-code rules injected into coding agents (root CLAUDE.md, Agent tools)"},
}


def folder_faults(tools, vendor):
    """vendor/ folders the table lacks, and rows whose folder is gone."""
    present = {path.name for path in vendor.iterdir() if path.is_dir()}
    return ([f"vendor/{name} is vendored but has no row in score/adapters/vendored" for name in sorted(present - set(tools))]
            + [f"{name} has a row but no vendor/{name}" for name in sorted(set(tools) - present)])


def caller_faults(name, row, repo):
    """Why a wired row's callers do not call its tool: a missing file, or one that never names it."""
    faults = []
    for caller in row["callers"]:
        path = repo / caller
        if not path.is_file():
            faults.append(f"{name}: caller {caller} is not there")
        elif not any(word in path.read_text(errors="replace") for word in row["names"]):
            faults.append(f"{name}: caller {caller} never names {' or '.join(row['names'])}")
    return faults


def row_faults(name, row, repo, images):
    """Why one row is off: a wired tool with no caller, image or stage that is there, any row without its why."""
    faults = [] if row.get("why") else [f"{name}: no why"]
    if row["use"] not in (WIRED, AGENT, LEFT_OUT):
        return faults + [f"{name}: use {row['use']!r} is not one of {WIRED}, {AGENT}, {LEFT_OUT}"]
    if row["use"] != WIRED:
        return faults
    if not row["callers"]:
        faults.append(f"{name}: wired with no caller")
    faults += caller_faults(name, row, repo)
    if row["image"] and not (images / row["image"]).is_dir():
        faults.append(f"{name}: image {row['image']} has no folder in tools/cloud/images")
    faults += [f"{name}: stage package score/stages/{stage} is not there" for stage in row["stages"]
               if not (repo / "score/stages" / stage).is_dir()]
    return faults


def faults(tools=None, repo=REPO):
    """Why the table and the repository disagree; [] when every vendored tool is accounted for."""
    tools = TOOLS if tools is None else tools
    found = folder_faults(tools, repo / "vendor")
    for name, row in sorted(tools.items()):
        found += row_faults(name, row, repo, repo / "tools/cloud/images")
    return found
