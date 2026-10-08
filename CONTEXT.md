# <PROJECT> — Domain Context

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

<Empty on purpose. The first `grill` session that sharpens a term writes it here. Do not seed this
section with guesses: a glossary of invented words is worse than no glossary, because skills treat
what is written here as canonical.>
