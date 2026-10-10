# The bible

The single source of truth for how this system works. One file, chaptered. A chapter ID is the
slug after the `##` (for example `architecture/system-context`), and the chapter map in root
[`CLAUDE.md`](../CLAUDE.md) points at it; link to a chapter as `docs/bible.md#architecturesystem-context`.

**How to use it.** Read the chapter the work touches, never the whole file. When you learn
something load-bearing that a future reader would otherwise have to re-derive from code, write it
into its chapter in the same session. When a chapter contradicts the code, the code wins and the
chapter gets fixed on the spot.

**What does not go here.** Vocabulary goes in [`CONTEXT.md`](../CONTEXT.md). Decisions that were
hard to reverse go in [`docs/adr/`](adr/). Status of ongoing work goes on its GitHub issue. The
bible holds how the thing works, not what we are doing about it.

A chapter that is still a placeholder says so in one line. An empty chapter is honest; an invented
one is not.

---

## architecture/system-context

<The big picture in one screen: what this system is, who or what talks to it, what it talks to.
Placeholder until the first real component exists.>

## architecture/components

The framework moved here from the game 2099 on 2026-10-08 (JoeyKardolus/2099#129), with its history (git
filter-repo on the moved paths). Two sides: the coordinating machine runs plain Python (plans, labels, checks, the
scene package; `.venv` from `pyproject.toml`), and every step that loads a model, bakes or renders runs on a rented
cloud machine that deletes itself (`tools/props/cloud/`, through the provider interface `provider.py`; Scaleway is
the current backend). No model runs on the coordinating machine.

- `tools/props/`: the prop pipeline (close-up to Pixal3D in a cloud batch, `cloud/batch.py`; finish; `pixal.py`),
  the scene tools (`scene/`: concepts, the world step, close-ups, inventories, layouts), the surface library and its
  piece making (`library/`: recipes, labels by parts, `make_chunky`/`make_kit` baked in the cloud, `route.py` for kit
  rooms, `place_route.py` for outdoor places, `package.py` for the scene package), the gates (`gates/`), Infinigen
  grounds and life (`infinigen/`). Each directory's rules are in its overlay.
- `tools/characters/`: the characters stage. `people/` builds each person's skinned, animated glTF (SOMA-X body
  shaped by SAM 3D Body, clips written by Kimodo from sentences, GarmentCode patterns draped by Newton's cloth solver;
  moved from 2099's `tools/crew` with its history). `maker/` is the character maker, one entry (`make.py`) for a
  person or an animal from a picture or a few words (`data/characters/makes/<name>.json`): a person's whole chain
  (picture, body by SAM3DBody-cpp, clips by Kimodo, drapes, head, hair by Hi3DGen, face by klein with a depth LoRA,
  build, UsdSkel, review renders) runs on one rented card (`tools/props/cloud/characters.py`), an animal's through
  `animals/`. `skel_usd.py` turns a body into a UsdSkel asset;
  `cast.py` writes a place's characters layer (`<stage>/layers/characters.usda`, between the edit layer and the
  base) from its cast in `data/characters/<place>.json`: named people, kit groups mixed by seed, and a crowd as one
  PointInstancer. The review page draws them (`tools/review/characters.py`).
- `tools/blender/`: the headless Blender launcher (never a window on the owner's screen).
- `tools/sound/`: the sound picker and the loudness rule; MOSS takes are made in the cloud.
- `data/library/`: the surface library (materials, fittings, composites, details per kind, printed pictures);
  `data/fonts/`: the fonts printed labels use (SIL OFL).
- The first world's data, the game 2099's, read as the example world: `data/definitions/place.json` (each place's
  style, palette, materials, wear), `design/tokens/tokens.json` (the palette), `data/inventory/` (scene
  inventories), `data/kit/` (laid kit rooms), `data/sound/` (the sound catalogue, briefs, licences and loudness).
- `tools/assets/`: the world's heavy files (made models, sounds) as a release of this repository, named with their
  sha256, source and licence by `data/assets/world1.json`; `world.py` fetches, checks, packs and publishes them, and
  every record names a file by its name there or by its path in git. The framework reads nothing from the game's
  checkout (2026-10-09, the owner: the game and SCORE are fully separate); `game_free_test.py` holds it so. An
  engine's own import of the package (the game 2099's Godot scenes for a kit) is that engine's adapter, kept in the
  engine's repository.
- `vendor/`: third-party tools as released, each pinned with its licence (ADR-0002).

**The output** of a place is its scene package (`package.py`): `objects/<name>.gltf` per object as baked, and
`scene.json` (`score.scene` v1: metres, y up, each copy's transform, its inventory row, its model check). The game's
Godot adapter stays in 2099. OpenUSD as the canonical scene format is the next task.

## architecture/lifecycles

**One outdoor place, end to end** (the wreck is the worked example; commands in the README):

1. The place's record: its picked concept, its scene inventory (`data/inventory/<place>.json`, one row per object
   with its size and spots), each kind's turn and allowed materials in `data/library/details.json`, and one close-up
   per generated row. Recorded inputs live in the work folder (`PROPS_WORK`), not in git (the pictures are large).
   The close-ups come from the close-up stage (`tools/props/closeup/stage.py`): Qwen-Image-Edit-2511 draws every
   one in a cloud batch, a shape check (cheap measurements and an open vision-language judge, tuned to fail rather
   than pass a wrong shape) accepts or fails each, and Nano Banana Pro draws only the failures.
2. Pixal3D models from the close-ups, one cloud batch (`cloud/batch.py`, refused without the approved inventory).
3. PartCrafter parts from each model's cut-out (`cloud/parts.py`), the painting unit.
4. Labels: every part one allowed library material (`library/labels.py`), checked for patchy paint; a take too long
   for one piece is split (`place_route.py split`).
5. The plan and the bake jobs (`place_route.py plan`), baked in the cloud (`cloud/library_bake.py`, `--processor`
   when no card is in stock).
6. The model gate and straightness (`place_route.py check`).
7. The scene package and its check (`package.py`).

## architecture/trust-boundaries

<Where untrusted input crosses into trusted code, how it is authenticated, where secrets live and
who can read them. Placeholder.>

## architecture/failure

<What breaks when each piece breaks, what the blast radius is, and how to recover. Placeholder.>

## build/release

Nothing is released yet but the paper. Commands, run locally (there is no CI and no GitHub Actions):

- `make paper`: builds the paper from `paper/source/score.md` with pandoc into `paper/out/score.tex`
  and `score.pdf` (citeproc, IEEE style) and into the arXiv tree `paper/arxiv/` (`main.tex`,
  `content/`, `figures/`, `refs.bib`, `main.bbl`, `main.pdf`). PDF engine: xelatex if installed,
  else tectonic. The build writes `paper/out/stamp.json`, the sha256 of every input (draft,
  bibliography, style, filter, figures, the build script) and every output.
- `make check`: the gate. `gate-scope.py` decides whether tests run (`paper/` counts as a build
  input, not a document); the tests include `paper/build/test_paper_current.py`, which fails when
  the files on disk no longer match the stamp, so a draft changed without a rebuild, or a
  generated file edited by hand, is red. Then the ADR index check.
- `make env` builds the framework's Python environment (`.venv`, `uv sync`); `make tests` runs every framework
  check (`tools/**/*_test.py`, plain scripts, each under a 16 GB memory cap), or only the ones named with
  `TESTS="..."`. `make check` runs them when code changed. While working, run only the checks your change touches.
  Render checks run Blender headless on a cloud machine, never here; nothing here runs Godot.
- `.githooks/pre-commit` (installed by `bootstrap.sh` as `core.hooksPath`) runs the same check on
  any commit that touches `paper/`. A green run means the committed PDF is the draft's.

**Scope the gate.** Running every test on every push stops scaling once several sessions work
side by side on one machine. The project's test command asks
`python3 .claude/scripts/gate-scope.py` first and reads its `MODE` line: `none` when the change
touches only documents and working notes (`.md`, `docs/`, `.claude/`), so nothing runs; `full`
otherwise. When the full run grows slow, grow the script into a graph that picks only the suites
a change can reach, and keep its rules:

- **Unknown means full.** A path the scope does not recognise, a file that went away and could
  have been named by something, no origin/main to compare with, `--full`, `GATE_FULL=1`, or a run
  on CI: everything runs. A new kind of path goes to full, never to "none".
- **A change to the gate itself runs everything**: the test runner, its config, vendored test
  frameworks, the CI workflow.
- **CI always runs everything.** It is the net under a test the scope misses, so it stays
  unscoped.
- **The scope has its own check against the real tree**: every suite is chosen when the file it
  is named after changes, and an exception is written down with the reason.
- **Print the reasons**, one line each, so whoever reads the gate's output sees what was skipped.

A grown version to copy from: the game 2099's `tools/test/scope/` (Godot scripts, scenes and
its resource paths).

## workflow/loop

The working loop, and the mechanisms that keep it from drifting.

**The loop.** Every conversation in this repo is a task, and it runs the same four steps.

1. **grill** — the first message in any conversation goes here, enforced by the `SessionStart`
   hook. Grill orients silently (the prompt, `.claude/soul.md`, root `CLAUDE.md`, the `CONTEXT.md`
   glossary, the bible chapters the prompt touches, the related GitHub issues), then interviews the
   plan one question at a time until the plan and the domain model agree. Facts get looked up, not
   asked. Decisions get asked, not assumed.
2. **to-prd** — the aligned plan becomes one PRD epic: a GitHub issue with a goal, a scope, a task
   list and a verifiable definition of done. No re-interviewing. A task that is independently
   grabbable, or that is going to an agent, is carved out as a natively linked sub-issue; everything
   else stays a checklist line.
3. **code** — the work itself, against the PRD.
4. **close** — ship what is done, write where the PRD stands, park every loose end under a parent
   PRD, and close the issue only when its acceptance list is genuinely met.

Two branches off step 1. A **brain dump** (several open questions at once, visionary thinking, a
pasted conversation) goes to `brain-dump`, which sorts it into claims, questions, decisions and
vision, sweeps and refutes, and lands each result in its own home. An effort that is **too big and
too fogged** for one session goes to `wayfinder`, which charts it as a PRD whose route is unknown
and breaks the fog into investigation sub-issues, one resolved per session.

**The mechanism stack.** Four types, one job each. Mixing them makes harness behaviour
unpredictable.

- **Skills** (`.claude/skills/<name>/SKILL.md`) hold methodology. Invoked by name (`/grill`) or by
  the model when the description matches.
- **Overlays** (`<area>/CLAUDE.md`) hold the rules for one directory and auto-load when a file in
  it is touched. A new code directory gets one without asking; it is the mechanism, not a document.
- **Hooks** (`.claude/settings.json`) hold automation that must fire on a harness event, not on the
  model remembering. Today: the grill protocol on `SessionStart`, the soul rules on every prompt,
  `md_guard` and `issue_guard` on `PreToolUse`, and the memory commit-and-push on `Stop`.
- **GitHub issues** hold the durable backlog. Anything that must survive the chat lives there.

**Sub-agents.** Independent steps go to sub-agents, and a sub-agent may split its own work over
sub-agents again (owner, 2026-10-09; heavy work runs in the cloud, so the old local-load cap is
gone). The parent writes each brief (task, scope, the rules that apply, where the result goes),
checks what comes back against the brief, and merges it; a sub-agent's word is never taken as
done. Each agent is short and scoped: one job, a clean context, and it ends when the job ends.
Waits run in the background, never as an idle agent. The coordinator watches every agent's age
and tokens and restarts, splits or stops a stale one without being asked (an agent alive for hours
or at hundreds of thousands of tokens on a small job is stale). Checked 2026-10-10: a session's
sub-agent spawned its own sub-agent and got its answer back; a sub-agent started by a workflow
script is not given the Agent tool and cannot nest.

**The board.** One GitHub project, created by `.claude/scripts/setup-github.py --board`. Status is
a board column, never a label: `LowPriority`, `Not started`, `In Progress`, `Review`, `Done`. Set it
with `python3 .claude/scripts/board-status.py <issue> "In Progress"`. Triage state is a label
(`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) and is a different
axis from the column; do not confuse them.

**Before you push.** Run the project's own test command (scoped by
`.claude/scripts/gate-scope.py`, see build/release), and
`python3 docs/adr/tools/check_index.py`. Both must exit clean. The push is the ship: this repo
works on `main` only (ADR-0001), so a push is visible to everyone immediately and there is no PR
step to catch anything you skipped.

**Commits.** Imperative and scoped: `module: description`. The scope is the module or area, not the
file. A commit that needs "and" in its subject line is two commits.

**Memory.** Claude's memory folder is linked into `.claude/memory` by
`.claude/scripts/bootstrap.sh`, and that folder is git-ignored: this repository is public, and
memory is private working notes. The `Stop` hook's memory commit finds nothing to commit. Memory
therefore does not survive a wiped machine; anything load-bearing goes into the bible, the
glossary or an issue instead.

## workflow/module-standard

The house standard for a module in this repo. It exists so that a reader can predict the shape of
code they have not seen yet.

- **One interface, one directory.** A module is a directory with an obvious way in. Callers import
  the way in, never a file inside it. Files that are not part of the interface are private
  (`_prefix` in Python, not exported in TypeScript, package-private in Java).
- **Deep over shallow.** A module earns its existence by hiding more than it exposes. If its
  interface is nearly as complicated as its implementation, it is a shallow module and belongs
  inlined into its caller. Vocabulary and the full argument:
  [`.claude/skills/improve-codebase-architecture/LANGUAGE.md`](../.claude/skills/improve-codebase-architecture/LANGUAGE.md).
- **One function, one purpose.** If the docstring needs "and" between two concerns, it is two
  functions.
- **Tests sit with the module** they test, named for the invariant rather than the function
  (`test_<invariant>`), and drive the module through its public interface. A test that reaches into
  the implementation freezes the implementation.
- **Failures propagate.** A write that can fail raises; it does not log and continue. The two tiers
  are: a failure the caller can do something about (raise a typed error) and a failure nothing can
  be done about (crash loudly). Swallowing is neither.
- **Every directory carries its overlay** (`CLAUDE.md`) once it has rules of its own.

<Extend this chapter with the specifics this project needs: the layer names, the test command, the
directory layout. The rules above hold whatever the language is.>

## workflow/bootstrap

Getting a fresh machine, or a wiped one, back to working.

1. Clone the repo, and install the GitHub CLI so `gh auth status` is green. The skills that touch
   issues and the board go through `gh`; without it, `to-prd`, `triage`, `close` and `my-issues`
   cannot run.
2. `bash .claude/scripts/bootstrap.sh`. It links `~/.claude/projects/<encoded-repo-path>/memory` to
   the repo's git-ignored `.claude/memory` (private, never pushed), runs
   `.claude/scripts/install-agent-tools.sh` (the agent tools in root `CLAUDE.md`: the pinned
   codebase-memory-mcp binary and Bun, each checked against its SHA-256; claude-mem's settings in
   `~/.claude-mem`; the vendored claude-mem plugin installed for this project; the repo indexed into
   `~/.cache/codebase-memory-mcp`), builds the framework's Python from `uv.lock` (`.venv`, and
   `~/.farm-factory-props/env` when missing, below), and reports anything else that is missing. It needs `node`,
   `python3`, `curl`, `uv` and the `claude` CLI. It is safe to re-run; every step skips what is already done.
3. `python3 .claude/scripts/setup-github.py --board` on a fresh repo only. Labels and the board are
   GitHub-side state and are not copied by "Use this template", so a repo spawned from the template
   starts without them.

**The framework's runtime** lives outside the repo, under `PROPS_HOME` (default `~/.farm-factory-props`, the first
world's name, kept so the cloud ledger, keys and work carry over): `cloud/` (the runner's ssh key, the self-delete
key, the spend ledger), `work/` (`PROPS_WORK`: takes, pictures, places' runs), `env/` (the interpreter the cloud
machine runner, `blender_cloud.py`'s `CLOUD_PYTHON`, and the animal route call: both hard-code
`~/.farm-factory-props/env` and ignore `PROPS_HOME`, so `bootstrap.sh` builds it there, from `uv.lock` without dev
tools, when it is missing; no model runs in it). The machines need `uv`, `make env`,
and the cloud backend's tools: for Scaleway, the current backend, the `scw` CLI logged in to the project named by
`SCORE_SCALEWAY_PROJECT` (by name, never an id).

**The character maker** (`tools/characters/maker/`) needs nothing installed here: every environment it runs is set up
on the rented card by `tools/props/cloud/characters_setup.sh` (about half an hour). It reads the secret
`hf-read-token` (a HuggingFace read token whose account accepted Meta's terms for `meta-llama/Meta-Llama-3-8B-Instruct`,
the base of Kimodo's text encoder), and from `MOTION_HOME` (default `~/.farm-factory-motion`) what every person shares:
the two boots (`look/work_boot.npz`, `look/space_boot.npz`), MakeHuman's CC0 base mesh and low-poly eyes, and the clips
already made (`work/motions/`); `make.py` names each (`SHARED`). A fresh box without them makes the clips again from
their sentences; the boots and the eyes' source files must be copied over.

**What survives a wipe:** everything in git. **What does not:** Claude's memory (git-ignored,
because the repository is public), `gh` auth, any local toolchain, and anything a session left
uncommitted.

## Identifiers

<The names and numbers a session needs and cannot derive: repository, board number, hosts, service
IDs, secret names. Keep it a table. Anything secret goes in a secret store, and only its name goes
here.>

| What | Value |
|---|---|
| Repository | `Babon-Innovations-b-v/score` |
| Project board | `9` (org project) |
| First user | the game 2099, `JoeyKardolus/2099` (paused 2026-10-08) |
| Cloud | backend chosen by `SCORE_CLOUD` (default `scaleway`); Scaleway: the project named by `SCORE_SCALEWAY_PROJECT` (default `farm-factory`), machines tagged `farm-factory-batch`; month ceiling `SCORE_MONTH_EUROS` (default 1500) |
| Secrets | read by name with `secret_store.secret(name)`: the environment variable `SCORE_SECRET_<NAME>`, else the backend's store (Scaleway Secret Manager in that project): `worldlabs-api-key`, `gemini-api-key`, `freesound-api-key` (optional) |
