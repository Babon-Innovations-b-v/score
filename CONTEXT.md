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
- **overseer** — the one session that coordinates the others running side by side: it hands out work, tracks what each is doing, and is who a session reports to when it ends. Found by name among the live sessions; it writes no code of its own. _Avoid_: hive, coordinator, lead, main session (main is the branch).
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
- **concept** — a picture of a place drawn from the creator's references and picked by the creator; it sets the place's structure and look and is never shipped. _Avoid_: key art, mockup, target (alone).
- **scene inventory** — the hard list of exactly what is in a place: every object a row with a kind, an anchor, a size in metres and a count, children anchored on their parent. Nothing is made or placed that is not a row. _Avoid_: object list, manifest, asset list.
- **close-up** — one clean, front-on picture of one object, drawn from its inventory row; the input to the prop pipeline and to the parts check. _Avoid_: crop (a crop is cut from a bigger picture), reference image.
- **code builder** — code a coding agent writes that builds one kind of object exactly (a wall plate, a door, a tool board). _Avoid_: procedural asset, handcrafted model.
- **prop pipeline** — the route's picture-to-3D branch: close-up, Pixal3D in a cloud batch, closed into a solid, triangles by size, straightness check. _Avoid_: generator, AI model step.
- **parts check** — the rule that routes a kind: built in code only when its code build shows every part its close-up shows, else the prop pipeline. _Avoid_: sorter (the sorter is the tool that applies it), shape rule.
- **surface library** — the one shared set of rule-based surfaces (ProcFunc functions, coloured from palette tokens, wear and seed as settings) every part of every piece is painted from; models and code give shape only. _Avoid_: material library, texture set, trim sheet.
- **room wear** — the one wear setting a room's surfaces share, with wear from a cause (edges, feet, drips). _Avoid_: weathering, dirt pass.
- **world step** — the optional stage that turns a picked concept into a walkable whole-room reference for later stages; never shipped. World Labs Marble in our runs; never compared with another model. _Avoid_: plan world (2099's older word), world model.
- **review tools** — what SCORE gives the creator to judge a place: pages with each stage's outputs side by side, before and after shots from the same cameras, in-engine walkthroughs and every check's result. How the creator judges with them is the creator's own. _Avoid_: blind pick, vote, approval gate.
