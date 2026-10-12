# SCORE — Domain Context

Canonical vocabulary for this codebase: the terms that mean something specific here, each with
the aliases to avoid (`_Avoid_:`). This is the working surface — [`grill`](.claude/skills/grill/)
challenges new terms against it and writes new ones here inline. Glossary only: no implementation
detail, no architecture prose. That lives in [`docs/bible.md`](docs/bible.md).

Format rules: [`.claude/skills/grill/CONTEXT-FORMAT.md`](.claude/skills/grill/CONTEXT-FORMAT.md).

## Language

- **soul** — the checked-in voice spec [`.claude/soul.md`](.claude/soul.md): the rules that fix how the assistant, and therefore most of this project's text, sounds. Every correction to the voice lands here as a rule, and the `UserPromptSubmit` hook in `.claude/settings.json` replays the rules verbatim on every prompt. Treated as a variable to pin down, not a preference. _Avoid_: persona file, style guide, tone guide, system prompt.
- **bible** — [`docs/bible.md`](docs/bible.md), one file, chaptered. The single source of truth for how the system works. _Avoid_: docs, wiki, handbook.
- **PRD** — a GitHub epic issue: one coherent module or workstream, with goal, scope, tasks and a verifiable definition of done. The unit of work and the planning surface. _Avoid_: epic (same thing, one name only), ticket, story.
- **sub-issue** — a task carved out from under a PRD, natively linked so the board nests it. Only for work that is independently grabbable or going `ready-for-agent`; everything else stays a checklist line. _Avoid_: child ticket, subtask.
- **overseer** — the session that guards drift: it holds the paper, the owner's vision and every standing rule, checks each captain on a schedule (commits, a plain status, the cloud) and sends short corrections that cite the rule or paper section they rest on. It reports to the owner and builds nothing itself. _Avoid_: hive, coordinator, lead, main session (main is the branch).
- **captain** — a session that runs one effort (world 1 through the framework, a research line): it plans the stages, briefs agents, checks and merges what they return, decides spend within the rules and reports to the overseer and the owner what changed in the result. _Avoid_: coordinator, manager, lead, overseer.
- **agent** — a coding agent a captain starts for one job with a written brief: it works in its own worktree, tests what it touched, pushes when its checks pass and reports what changed in the result. It may split its work over sub-agents. _Avoid_: worker, builder, bot.
- **sub-agent** — an agent started by an agent for one narrow step (a search, a render, one fix, a measurement): it returns its result to its parent and never reports to the owner or takes on new scope. _Avoid_: helper, child agent, subtask.
- **overlay** — a per-directory `CLAUDE.md` that the harness auto-loads when a file in that directory is touched. _Avoid_: local rules, sub-config.

## Architecture vocabulary (Pocock's laws)

The core depth/seam vocabulary used by `improve-codebase-architecture`, `tdd`, `diagnose`, `to-prd`. Full definitions: [`.claude/skills/improve-codebase-architecture/LANGUAGE.md`](.claude/skills/improve-codebase-architecture/LANGUAGE.md).

- **module** — anything with an interface and an implementation. _Avoid_: unit, component, service.
- **interface** — everything a caller must know: types, invariants, ordering, errors, config, perf. _Avoid_: API, signature.
- **implementation** — code inside the module. _Avoid_: internals, body.
- **depth** — leverage at the interface. _Avoid_: thickness, size.
- **deep** — small interface, lots of behaviour behind it.
- **shallow** — interface nearly as complex as the implementation. _Avoid_: thin, anaemic.
- **seam** — where an interface lives. _Avoid_: boundary.
- **adapter** — concrete thing satisfying an interface at a seam. _Avoid_: impl, plugin.
- **port** — interface defined for cross-seam dependencies.
- **leverage** — what callers get from depth. _Avoid_: reuse.
- **locality** — what maintainers get from depth. _Avoid_: cohesion.
- **deletion test** — imagine deleting the module: complexity vanishes → kill; reappears across N callers → deepen.
- **wide layer** — `ls` >12 entries (ignoring build output, caches, `node_modules`, `.venv`, `.git`). Missing boundary. _Avoid_: bloated, junk drawer.
- **split-brain** — same domain in 2+ top-level dirs sharing a name. Fix: pick one home or rename. _Avoid_: scattered, duplicated.
- **deepen** — collapse a wide layer behind ≤7 public symbols; internal files private (`_prefix`).
- **group** — sort a flat pile into named subdirs; no interface change.
- **no-loose-files rule** — every dir = subdirs only, plus a framework carve-out list. ADR-0002 holds the why and the amendment procedure; the authoritative carve-out list is in root `CLAUDE.md`. _Avoid_: top-layer-cleanup, no-floaters.

## Project vocabulary

Carried over from the framework's first user, the game 2099 (its `CONTEXT.md`, 2026-10-02 to 10-08), where these words were sharpened with the owner.

- **SCORE** — the framework, and the paper's name: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments". The creator writes the score; coding agents and open tools play it. Written in capitals. Not WorldScore (a benchmark), not score distillation in text-to-3D, not DeepMind's SCoRe. _Avoid_: Score, the score framework, HAVFM.
- **framework** — SCORE as a whole: the stages, checks, libraries and review tools that turn a creator's picks, offline and in cloud batches, into a fixed, owned, editable world an engine loads; nothing is generated while the world is played. _Avoid_: world compiler, world model (a model that renders frames), pipeline (alone).
- **route** — the sequence of stages one place is built through, with its rules and checks. _Avoid_: workflow (alone), recipe.
- **place** — one part of a world with a look of its own (a room, the ground round a base), built by one run of the route. _Avoid_: level, location, area, zone.
- **neighbour** — another place a place shows (the square and the far city past the launch), listed in its scene record's `places` and stood in its stage as that place's own accepted assembly, without the neighbour's own neighbours. _Avoid_: adjacent place, linked place, sub-scene.
- **concept** — a picture of a place drawn from the creator's references and picked by the creator; it sets the place's structure and look and is never shipped. _Avoid_: key art, mockup, target (alone).
- **scene inventory** — the hard list of exactly what is in a place: every object a row with a kind, an anchor, a size in metres and a count, children anchored on their parent. Nothing is made or placed that is not a row. _Avoid_: object list, manifest, asset list.
- **close-up** — one clean, front-on picture of one object, drawn from its inventory row; the input to the prop pipeline and to the parts check. _Avoid_: crop (a crop is cut from a bigger picture), reference image.
- **code builder** — code a coding agent writes that builds one kind of object exactly (a wall plate, a door, a tool board). _Avoid_: procedural asset, handcrafted model.
- **scene record** — a place's record of what no made piece covers (shells, stairs, gameplay objects, ground and water, backdrop, lights, sky, the neighbours it shows) and the cameras it is judged from, as numbers its code builders and the stage read; written by the scene-record stage from the place's plan (world 1's first records were transcribed from the game, and are now seeds). _Avoid_: scene file, extras, game-only layer.
- **plan** — a place's dimensioned drawing in metres (`data/plans/<place>.json`): its walls, doors and where each leads, its items with the inventory rows that make them, its keep-clear zones and standing spots, and its concept read element by element. _Avoid_: layout (the inventory's laid spots), floor plan, blueprint.
- **prop pipeline** — the route's picture-to-3D branch: close-up, Pixal3D in a cloud batch, closed into a solid, triangles by size, straightness check. _Avoid_: generator, AI model step.
- **parts check** — the rule that routes a kind: built in code only when its code build shows every part its close-up shows, else the prop pipeline. _Avoid_: sorter (the sorter is the tool that applies it), shape rule.
- **surface library** — the one shared set of rule-based surfaces (ProcFunc functions, coloured from palette tokens, wear and seed as settings) every part of every piece is painted from; models and code give shape only. _Avoid_: material library, texture set, trim sheet.
- **finish map** — a flat-colour copy of a model's close-up: the same outline and framing, every finish one solid label colour on a plain background, each label tied to one surface of the surface library; used to split the model into parts by finish. _Avoid_: label map, segmentation mask, colour map, part map (a part map shows the split itself).
- **room wear** — the one wear setting a room's surfaces share, with wear from a cause (edges, feet, drips). _Avoid_: weathering, dirt pass.
- **world step** — the optional stage that turns a picked concept into a walkable whole-room reference for later stages; never shipped. World Labs Marble in our runs; never compared with another model. _Avoid_: plan world (2099's older word), world model.
- **review tools** — what SCORE gives the creator to judge a place: pages with each stage's outputs side by side, before and after shots from the same cameras, in-engine walkthroughs and every check's result. How the creator judges with them is the creator's own. _Avoid_: blind pick, vote, approval gate.
- **picked viewpoint** — a view the creator saved while walking a place in the viewer (eye, aim, fov, a name), kept in `data/review/<place>/viewpoints.json`; a place's films start from its picked viewpoints when it has any. _Avoid_: bookmark, saved camera, pick (alone: a pick is a model the creator chose for a row).
- **capability class** — what a cloud job needs from a machine, named without a provider: `gpu-<GB>gb` (one card with that much memory), `gpu-<GB>gb-x<N>` (N such cards), `cpu-<cores>c-<GB>gb` (a processor machine). Runners ask for classes; the cloud backend maps each to its own machine types. _Avoid_: machine type, instance type, card type (these are a provider's names).
- **parked machine** — a machine kept after its run (its files removed, its set-up kept) for the next run of the same kind to take instead of renting (`tools/props/cloud/park.py`): a processor machine billed by the started hour until 5 min before its paid hour ends, a card for its kind's measured cold start (at most 10 min). Never idle past that. _Avoid_: warm machine, warm card, pool, kept machine.
- **cloud backend** — one cloud provider behind the framework's provider interface (`tools/props/cloud/provider.py`), holding that provider's machine types, zones, prices, secret store and self-delete. Scaleway is the current one. _Avoid_: cloud (alone), provider module, Scaleway (for the interface).
- **character** — a person or animal in a place, made from the place's data, rigged and playing a clip: a skinned UsdSkel asset in the place's stage. _Avoid_: NPC, actor, avatar, agent (an agent is a coding agent).
- **cast** — the record of a place's characters, `data/characters/<place>.json`: who is there, how many, where, doing what, and why each is there; nothing is placed that is not an entry. _Avoid_: spawn list, population, NPC list.
- **crowd** — many copies of one cheap character body in a few clips, phases and palettes of clothes, laid as one instancer; anybody within reach of the viewer is a character of their own instead. _Avoid_: extras, background people, swarm.
- **stage** — one fixed step of the route, with a stated input and output, gates and a review page (concept, plan, inventory, layout, assembly, settle, the layers, complete; close-up, shape, parts, surfaces per object). A row of the stage table in `score/stages`. _Avoid_: step (alone), phase, task.
- **node** — one stage for one place (`assembly@hangar`), or for the whole world; what the runner keys, makes, judges and accepts. _Avoid_: job (a job is a cloud run), target, asset.
- **finish record** — what a node's run leaves in the store: its key, output, every input's hash, its code version, commit, seed, parameters, machine, time and cost. No record counts as not run. _Avoid_: log, manifest, run info.
- **gate** — a stage's check between it and the next: it answers pass, fail or unknown with measures and a reason; unknown blocks like fail, and missing evidence is unknown. _Avoid_: test, validation, guard (a guard is a hook).
- **accepted output** — the output of a node that stands accepted; the only one later stages read. The runner accepts an output by itself when every gate passed and no score got worse (an automatic accept, its record says so); the owner may reject any accepted output, which moves it back to the one accepted before and makes every later node that read it stale, or accept a worse one with his reason. _Avoid_: canonical, latest, current take, approved.
- **clearance** — the runner's leave for one paid run of a node: given when every gate on its inputs passed and they stand accepted, and the month's ceiling has room for its estimate; kept in the store, and the only thing besides the owner's override that lets a rent point spend. _Avoid_: spend yes (that is the owner's override), approval, budget.
- **unverified seed** — an old output brought into the store as a stage's output (hashed, its origin shown) that no gate has judged yet; never accepted until its stage reruns or checks it. _Avoid_: legacy output, baseline, import.
- **contract** — a stage output's schema, version and units (metres, seconds, degrees, Y up), stamped into the output as `contract.json`, checked by the stage that makes it before it is stored and by every stage that reads it. _Avoid_: format, spec, interface (an interface is a module's way in).
- **waiver** — the owner's word that one check of one node counts as passed under one key, with his reason; it ends when the key changes and shows on the review page and in status. _Avoid_: override, exception, skip.
