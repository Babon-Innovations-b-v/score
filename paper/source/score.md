---
title: "SCORE: Synthesizing Complete, Owned, Responsive Environments for Simulation"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 27 October 2026"
abstract: |
  Games, film, robot learning and embodied AI all depend on 3D environments that can be simulated, in which every object is a body of its own with collision, mass and joints, stands under the gravity of the ground beneath it, can be changed afterwards, and belongs to the person who made it. Current generative methods rarely deliver this: world models produce frames that no simulator can step, and one-shot 3D generators produce a single fused scene without separate bodies or clear rights to the result. We present SCORE, a framework that synthesises such environments by building them the way film studios build scenes in OpenUSD. Each scene sits within its parent scene, and each kind of work on it (layout, surfaces, physics, light, motion, effects, sound and people) is a layer of its own that is checked and changed independently of the others. The creator locks the design from the top down, first an environment concept that fixes its style and its physics and then a concept for each scene; open vision foundation models, procedural tools and coding agents then make every layer below, each checked by measured gates before the next is made. Every model in the framework allows commercial use of its output, so the creator remains the author, and every step is keyed on its inputs, so an edit reruns only the steps that depend on it. The result is a single OpenUSD environment whose physics a simulator reads as written; Newton, with MuJoCo's solver, steps it, and each character in it receives a sim body on Newton driven by its SOMA segment rotations. We describe the framework and its method, with a first environment as the evidence; its four demonstrations are marked as gaps until its batch has run. We close with the route toward simulated bodies that are true to the individual person and trained models that drive them. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT licence).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main claim: the framework, which synthesizes complete, owned, editable environments that are
    physically simulable and usable across games, film, robotics and embodied AI; building environments
    is its method, environment 1 its evidence (owner, 2026-10-27).
  - About 4 to 5 pages plus references while gaps are open.
  - Every number is read from a file, commit or issue comment named in a comment beside it.
  - No demo or result from a lost or rejected run: every figure, table and film of environment 1 is a gap
    box until its batch has made it (owner, 2026-10-21). The four demonstrations: owner, 2026-10-27.
  - The walkable reference is one optional step; no result compares it with another model or judges it
    on its own, and its output is credited "Generated using World Labs".
  - Tone: the owner's previous paper, arXiv:2607.17639 (owner, 2026-10-27).
-->

```{=latex}
\makeatletter\def\fps@figure{tp}\makeatother\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.1}
```

::: gap
**Gap: Figure 1, one environment, every layer.** Environment 1 from the top down: its physics (the bodies it stands on and their gravity), a top scene on its site, a parent scene with its child scenes, and one scene opened into its layers side by side (base, settle, physics, light, motion, effects, sound, people). It waits on environment 1's batch.
:::

# Introduction

Simulated 3D environments have become raw material for games, film, robot learning and embodied AI [@yang2024holodeck]. What these uses have in common is not a particular look but a structure: separate objects with collision, mass and joints, ground with its own gravity, light and sound that come from a source in the scene, and a scene that can be opened, changed and simulated again. Building such an environment by hand is expensive, and this has made generative methods attractive; yet a generator that takes over the work must leave the result in its maker's hands, and many of those makers are sceptical, with 52 percent of game workers in GDC's 2026 survey reporting that they thought generative AI was hurting their industry [@gdc2026survey].

The generative methods available today fall short of that structure in different ways. World models generate an environment as a sequence of frames [@bruce2024genie; @genie3], which no simulator can step. 3D environment generators [@wang2025worldgen; @hyworld2] produce geometry, but mostly as one fused asset from which separate objects have to be recovered afterwards [@hu2026worldact; @niu2026worldsculpt]. Both work in a single shot, so a fault in the result cannot be traced back to the step that caused it. Procedural systems [@raistrick2023infinigen] and coding agents that write scenes as programs [@hu2024scenecraft; @wang2026codeasworlds] keep the environment explicit, but they rebuild scenes that already exist or draw from a fixed library, and their objects often float or come apart [@gao2026codebench3d]. Open vision foundation models [@oquab2023dinov2] can now read shapes [@li2026pixal3d], masks [@carion2025sam3] and depth [@wang2025moge2] from pictures, and a coding agent can connect them as tools, but none of them keeps one style across objects that different models made [@wu2026production; @yang2026flowscene], and none of them provides physics.

The pieces needed for the physics do exist. OpenUSD [@openusd], the scene description Pixar developed for its films, keeps each department's work in a layer of its own and assembles scenes from smaller ones by reference, and its physics schema states bodies, colliders, mass and joints within the same stage. MuJoCo [@todorov2012mujoco] is a widely used solver for articulated bodies in contact, and Newton [@newton], built on Warp [@warp], runs MuJoCo's solver on the GPU [@mujocowarp] and reads OpenUSD directly. What is missing is a way to get from what a creator wants to a complete environment in that form.

<!-- OpenUSD: openusd.org "Introduction to USD" (each artist works in their own file, a layer; references assemble assets into scenes), read 2026-10-21. Newton reads the composed stage (add_usd): score/stages/physics/inside/physics_trial.py docstring. MuJoCo Warp maintained by Google DeepMind and NVIDIA as part of the Newton project: github.com/google-deepmind/mujoco_warp README, read 2026-10-27. -->

We observe that an environment need not be generated in one shot to be generated automatically. Studios already build scenes as a tree of smaller scenes, each a stack of layers that one department makes and another can change without touching the rest, and the same structure lets a machine build an environment one checked step at a time. If every layer is made from a design the creator has locked, by a step whose output is measured before anything is built on it, then a fault has an address, an edit has a bounded cost, and the physics can be written into the record itself rather than recovered from it.

This paper contributes not a new generative model but a framework that turns a creator's locked design into one OpenUSD environment which a simulator steps as written. What is new is the combination of three elements: a design locked from the top down, from an environment concept with its style and physics to a concept for every scene, from which every layer is read; layers made by keyed steps, each held to measured gates, so that an edit reruns only what it changes; and a record whose bodies, joints and gravity are written in OpenUSD's physics schema, made only with models that allow commercial use of their output. The environments this yields are what the name SCORE describes. They are complete, in that every object, surface, light and sound a scene shows exists wherever the viewer looks; owned, because every model in the framework allows commercial use of its output, so the creator holds the full rights; and responsive, because every object has its collider, mass and material and what moves has its joints. They are also editable, since each scene is a stack of layers and each layer is made by a keyed step. An environment can be as small as a house on a plot of ground or as large as a system of worlds that move one another.

Section 2 describes the framework, Section 3 its method, the stages that build a scene from the top down and layer by layer, and Section 4 the evidence, four demonstrations on a first environment that remain gaps until its batch has run. Section 5 discusses what the design implies and where it is limited, Section 6 positions it against related work, and Section 7 sets out where the framework goes next, toward simulated people who are true to the individual person.

<!-- Uses and the main claim: owner, 2026-10-27 (this rewrite's brief). Scales of an environment: CONTEXT.md "physics" (owner 2026-10-21). -->

# The framework

An environment in SCORE is one OpenUSD record. Each scene is one stage, which sits within its parent scene and holds its child scenes, each referenced at the room its parent's plan gives it, so that opening a top scene opens everything below it. Within a scene the layers stack in a fixed order: a slot for the creator's edit layer on top, then people, sound, light, motion, effects, crops, machines, physics, settle and ground, and at the bottom the base laid from the locked plan. Each object corresponds to one real-world object and carries its kind, its transform, its collider and a library surface for each of its parts.

The physics of an environment is decided in its environment concept (EC). It may be a plot of ground with a gravity and a path of the sun, one world, or a system of bodies that move one another; a real body takes its values from a cited table, and an invented one is given by its radius, mass, orbit and spin. The physics layer writes each scene's bodies, masses, joints and the gravity of the body it stands on in OpenUSD's physics schema, so that any reader of that schema obtains the same scene.

<!-- Layer order: score/stages/assembly/record.py ORDER. Scene tree: score/stages/assembly/scene_tree.py, commit 8f07a249. Physics: CONTEXT.md "physics" (owner 2026-10-21); score/review/setting.py (data/physics/bodies.json, the cited table); score/stages/physics (design.py), tools/usd/physics.py ("written so any UsdPhysics reader gets the same trial": issue #55 comment https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441190720). -->

The creator works in the creator cockpit, a single signed-in web page in which he locks the design, buys paid work and reviews what the framework reports. Beneath that page, an environment is a table of stages read off its designs; for environment 1 the table has 261 rows. A node is one stage applied to one scene (for example `assembly@hangar`) or to the environment as a whole, and a single runner makes, judges and accepts every node. Once a design is approved, everything runs without a further yes from the creator.

<!-- 261 rows: len(score.stages.STAGES) at 68378cc4. The cockpit: CONTEXT.md "creator cockpit"; score/dashboard. Design before the batch: owner 2026-10-20, issue #10 comment 2026-10-20T18:00:28Z. -->

Three mechanisms make this safe to leave running. The first is the key. A node is made only when its key has no finish record, and the key hashes the stage and scene, its code version, contracts, parameters and seed, the pinned model images, every file the node reads and the accepted output of every node it reads. The code version counts only code that can shape the output; code that decides where and how a job runs changes what a run costs but never what it makes, and is therefore kept out of the key. An edit or a fixed fault moves only its own key and those downstream of it, so only those steps run again, and outputs are kept by content hash and never overwritten.

The second is the gate. Each gate answers pass, fail or unknown, together with its measures and a reason; missing evidence counts as unknown, and unknown blocks a node just as fail does. The runner accepts an output by itself when every gate has passed and the output is no worse than the one accepted before it, and later nodes read only accepted outputs. The creator keeps four actions for himself: he may reject an accepted output, which makes every node that read it stale; accept a worse one with a reason; waive one gate for one key; and override the runner for one paid run. A store that refuses these records when they come from an agent's process, together with a hook, keeps agents from taking these actions.

The third is the batch. Paid work is bought as a batch with a single estimate, and the creator's approval sets one budget for the batch across all its tries, at which the money guards stop it. Within a batch every paid job runs once, and an output that fails becomes a batch gap that the completion gate lists. Every paid stage is priced from a unit cost measured on the ledgers; a stage that has never run has no measured price, so its estimate is shown separately as a guess.

<!-- Keys: score/graph/__init__.py (own_parts, worked_out_key, node_seed, code, usable), score/graph/_code.py (source_files, FRAMEWORK); commit c3b60928. Gates: score/checks (judge, missing_evidence, overall, blocks, regressions). Accepts and the creator's actions: score/review/__init__.py (accept_automatically, accept, reject, waive), score/store OWNER_AREAS, .claude/hooks/accept_guard.py. Batches: CONTEXT.md "batch", "try" (owner 2026-10-20, 2026-10-26); score/dashboard/checkout/flow.py batch_budget; batch gaps: score/stages/batch_gaps.py, commit 1b61643d. Prices: data/costs/per-unit.json, tools/costs/per_unit.py; guesses kept apart: score/adapters/compute run_price (guess_euros). -->

# Method: building an environment

The method has two parts. The first turns what the creator wants into a locked design: a concept for the environment and for each of its scenes, an inventory of every object, and a plan in metres. The second reads the layers each scene needs off that design and makes each in turn, behind its gates, until the scene passes its completion gate.

## From concept to plan

Step 1: the environment concept. The creator first locks the EC in a short interview with Gemini 3.1 Pro [@gemini31pro], in which he fixes its style and its physics, adds his reference pictures and names the scenes it holds. An environment plan then places each top scene's site on that ground and works out the sky each site sees.

Step 2: a concept for each scene. A concept is then locked for every scene, in the order of parent scene before child scene. Each draw is one Nano Banana Pro [@nanobananapro] call, made on a concept review page where the creator can mark areas and ask for a new draw. A child scene is drawn only once its parent has been locked and planned, and it is drawn on a crop of the parent's concept, so that it fits the parent it stands in.

Step 3: inventory and plan. Gemini 3.1 Pro lists every object of the locked concept as a row of the scene inventory, giving its kind, count, anchor and size in metres, and SAM 3 [@carion2025sam3] draws a box around each row; nothing that is not a row is made or placed. Nano Banana Pro then draws the scene from straight above, and Gemini 3.1 Pro writes the plan in metres from that drawing, the concept and the inventory. The plan gives the outline, walls, openings, levels, stairs, roofs and terrain, each item with its facing, people as the spots on which they stand, and the rooms of the child scenes. A set of free checks follows: every row must be placed as often as its count says, lie inside the outline and not overlap another floor item, every door and standing spot must be reachable on foot, and the child scenes must tile their parent. What fails is returned to the model as notes at most twice, and only what is left after that becomes a gap. The creator's own edits on the plan review page always take precedence and redo what follows from them.

<!-- CONTEXT.md: environment concept, environment plan, concept review, plan review, scene inventory. Code: score/review/environment_concept.py, environment_plan.py, sky.py, concepts.py, reading.py (gemini-3.1-pro-preview; SAM 3 boxes), plan_drawing.py, plan_writing.py, plan_checks (placed, outside, overlap, reach, tiling), plan_fixes.py (at most two notes rounds, commit dcc9bb14), plans.py (commits 2604f113, d307de88). -->

The route is the same loop at every scale, so that shapes are fixed before detail. A parent scene receives its concept, its plan and a rough model; its plan is then split into the shapes of its child scenes, and once those shapes are fixed every child scene is made in parallel, each repeating the loop. The two stages that carry this, `rough-model` and `shell-split`, are built but have not yet run.

<!-- The creator's order: owner, 2026-10-19, issues #10 and #11. Rows: score/stages/rough_model (#15), score/stages/shell_split (#16). No run: paper/evidence/design/design-2026-10-21.txt (rough-model and shell-split records: 0). -->

## Layers from row kinds

A scene's layers are read off its design alone. Each inventory row's kind, found from the noun the reading gave it by a single table of rules, says what its objects do: emit, move, lie loose, glow, grow, act or sound. A scene receives an effects, motion, physics, crops or people layer only when it has rows that do so, and always receives light and sound. Each layer is made from its rows by the rule for their kind, so a new environment needs no hand-written list of what to build. The scene record holds what no made object covers (shells, stairs, ground and water, backdrop, lamps and neighbouring buildings), and it is gated on the shell lying within 5 cm of the plan and on every doorway opening onto a floor.

<!-- Row kinds: score/stages/row_kinds.py, data/checks/row-kinds.json, score/stages/design_layers.py, commits be088c14, 99d19861, d8012846. Scene record: score/stages/scene_record (gates.py: game-free, plan-matched, openings, TOLERANCE = 0.05). -->

Models are made by the prop route first. Nano Banana Pro draws a close-up of each object from its crop of the concept, redrawn at most three times when the shape check rejects it; Pixal3D [@li2026pixal3d] builds the model from that close-up; and a likeness gate compares the model's outline from eight sides with the close-up. Only an object whose checks fail is built instead by a code builder that a coding agent writes, and a thin straight object (a pipe, post or beam) whose every close-up has failed is swept along its length in code.

<!-- Prop route first: score/stages/props/CLAUDE.md (owner 2026-10-12). Retries: tools/props/closeup/stage.py PRO_TAKES (owner 2026-10-24). Likeness: likeness.py (eight outlines). Thin straight things: commit 546a2ba3 (owner 2026-10-25). -->

Surfaces come from the creator's library. Everything a scene shows is drawn from score_lib or recorded as a written exception, and a model contributes its shape only. Each of its parts takes one surface from a library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen] and coloured from the scene's palette. The finish route labels each face from free renders of the model, matches each finish to a library surface, bakes it, and checks the bake against the close-up, requiring each finish to lie within ΔE 32 of its colour there. A free library check then traces every material, model, light, sound and character of an accepted assembly back to the library or to an exception.

<!-- The library rule: owner 2026-10-18, commit 4c8d3b4d; data/checks/library-exceptions.json; score/stages/complete/library. Finish route: score/stages/surfaces/CLAUDE.md (owner 2026-10-20, #18), finish_parts.COLOUR_DELTA_E 32, commit 5c1e82b6; bake_check.py CLOSE_UP_DELTA_E 32.0. -->

## Settling and physics

Loose objects are dropped onto the made ground, and the settle writes where each comes to rest as a layer of its own; an object that would turn by more than 15 degrees or drift by more than 30 cm is recorded as a resting fault and keeps its laid pose. The physics trial then steps the composed scene on Newton, using MuJoCo's solver on Newton's contacts under the gravity of the body the scene stands on, and judges it by four gates: `reacted`, `at rest`, `energy`, which requires that undriven energy does not rise, and `hinge`, which requires a hinged leaf to swing to its limit.

The trial moved from Blender's Bullet [@bullet] to Newton on 27 October 2026, and the move was checked on a toy scene at Moon gravity with two crate drops, a driven door with a wheel fixed to it and a pushed stool. Both engines gave the same answer on every gate, and Newton landed the crates on their targets where Bullet left them on its 8 mm contact margins. Newton's deterministic mode was bitwise equal over six runs on that toy, but it cannot hold scenes with many loose bodies, because its buffers then pass the 32-bit limit; the trial and the settle therefore run without it, and two runs of a 25-body toy agree within 5e-7 m on every body except one that falls off the edge of the floor. <!-- deterministic six runs: https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441728558; 25-body toy without it: https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6446507856 --> The settle is moving to Newton in the same way, so that one engine steps both what comes to rest and what is tried, and one effect is to be stepped on Newton as a first case for the effects layer.

<!-- Settle and one effect on Newton, part of the framework before shipping: owner, 2026-10-27 (this rewrite's brief); settle today on Bullet: tools/usd/settle.py. tools/usd/settle.py TURN_MOST 15, DRIFT_MOST 0.3; score/stages/settling. Physics trial on Newton: commit c76fc1e4; score/stages/physics/inside/physics_trial.py. Decision to replace Bullet outright: https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6440766961 (owner, 2026-10-27). Bullet baseline (Moon gravity 1.62 m/s^2, +0.008 m over table and floor): https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6440856171. Newton on the same toy (+0.000 m, same gate answers: reacted, hinge, energy pass, at rest fail for the pushed stool in both): https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441190720. Six runs bitwise equal with Newton 1.7.0 deterministic (not pinned yet, two-week rule): https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441728558. -->

## Light, motion, effects and sound

The sky is computed from the EC's physics rather than drawn, with each body placed at its true direction, size and phase as seen from the scene's site. The lamps are the inventory's glowing rows: one render per scene gives each lamp its own light group, and a free sweep mixes their strengths until the scene lies within 1.5 times its concept's brightness. Every object of a moving row moves by the rule for its kind, at a speed cited from real machines, and is gated on nothing passing within 3 cm of anything else. Emitters are measured against real footage, and each sound source receives either a library file or one MOSS-SoundEffect [@moss2026] take, gated on a CLAP [@wu2022clap] score of at least 0.30.

<!-- Sky: score/review/overhead.py, score/stages/light/sky.py. Light: score/stages/light/mix.py (BRIGHT_WITHIN 1.5). Motion: score/stages/motion, data/checks/motion.json, REACH_MOST 0.03. Effects: score/stages/effects, data/checks/effects.json. Sound: score/stages/sound/gates.py CLAP_FLOOR 0.30. -->

## People and sim bodies

People are made like any other model, from a close-up per person row that Pixal3D builds and the finish route paints. SOMA's body [@saito2026soma], read from the close-up by SAM 3D Body [@yang2026sam3dbody], is fitted beneath the model as its rig, and Kimodo's clips [@rempe2026kimodo] move it; a shell gate passes a look when 99 percent of its soft points lie within 5 cm of the body. Each person stands on a person spot of its scene's plan.

Each character also receives a sim body, its physical twin on Newton, so that the people in an environment are simulated and not only animated. The minimal body is built directly from SOMA's 23 segments, with a ball joint at each SOMA joint frame, and is driven by the character's SOMA segment rotations without scaling or per-person setup. Its mass is distributed by segment volume, and it stands on a SCORE floor, so its ground forces come from contact; muscles enter as a minimal first step. Built in this way, the body follows SOMA's rotations to within 6.9e-9 m, and on Newton it matches plain MuJoCo to within 3.4e-8 after 200 steps.

<!-- score/stages/people/CLAUDE.md; score/stages/people_bodies/bodies.py (SHELL_SHARE 0.99, OFFSET_MOST 0.05); score/stages/cast. Sim body: CONTEXT.md "sim body"; issue #56 (Destination); minimal first, part of the framework: owner, 2026-10-27 (this rewrite's brief). 23 segments, 6.9e-9 m, 3.4e-8 after 200 steps (Newton 1.6.1 against plain MuJoCo): https://github.com/Babon-Innovations-b-v/score/issues/58#issuecomment-6441806660. -->

::: gap
**Gap: Newton for the settle, one effect and the sim body.** The settle and the physics trial on one engine, with the resting and physics gates per scene against the Bullet settle; the one effect stepped on Newton; and a sim body walking on a SCORE floor, its joint angles and ground forces against OpenCap's LabValidation motion capture and force plates [@uhlrich2023opencap]. It waits on these three stages being built and run on a cloud card.
:::

## Completion

A scene is complete when its completion gate passes on its final assembly, which requires every row to be made or dropped with a reason, nothing to be left unmade, no resting fault, and every layer and every shown scene to be present. A fault the creator decides to ship with becomes an accepted gap, recorded with who decided, when and why; the gate lists every gap by name and is never loosened. A hook stops an agent from claiming that a scene is done while its gate fails, because agents judging their own scenes agree with a measured geometry score only 45.8 percent of the time [@li2026lego]. Once a scene is complete, its films are made from scripts the creator has locked.

<!-- score/stages/gaps.py; tools/usd/complete.py CHECKS; .claude/hooks/completion_guard.py. LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. Films: score/stages/demo_film, commits 8c89174a, fe4c675d. -->

# Evidence: environment 1

Environment 1 is the evidence for the framework. Its first run was not accepted by the creator, and its store was lost on 19 October 2026, so this draft shows none of its outputs; each demonstration below will be made on its new batch, Figure 1 being the first.

<!-- The creator's review: issue #10 body. The loss: docs/bible.md architecture/failure ("Losing $PROPS_HOME", 2026-10-19, #13). Demonstrations: owner, 2026-10-27. -->

::: gap
**Gap: Demonstration 2, physics that holds.** Environment 1's scenes stepped on Newton under their own body's gravity: loose objects come to rest, doors swing on their hinges, with the physics trial's gates per scene and Bullet run on the same scenes as the baseline. It waits on environment 1's batch and on Newton taking over the settle.
:::

::: gap
**Gap: Demonstration 3, one environment, many uses.** The same OpenUSD environment opened unchanged in a game engine, in a robot simulator and in a film render, with what each reads of its layers and what it drops. It waits on environment 1's batch and on the engine adapter.
:::

::: gap
**Gap: Demonstration 4, an edit that stays cheap.** The creator changes one thing in a locked scene, and only the nodes whose keys it moves run again; the nodes rerun, time and euros against a full rebuild. It waits on environment 1's batch and on the edit layer being carried from one assembly to the next.
:::

::: gap
**Gap: Table 1.** Per scene of environment 1: inventory rows, models generated and code-built, layers, gaps before and after the batch, time, euros and the creator's verdict. It waits on environment 1's batch and the creator's review.
:::

The division of labour behind this work is as follows. The creator's locks, picks, accepts and waivers are his own clicks, and everything between them runs automatically. Coding agents wrote most of the framework's code under the author's direction: 2,413 of its 2,436 commits carry a coding agent as co-author. Hand fixes to a scene are recorded as the creator's edits.

<!-- Commits: git log at 2f6c81ef (rev-list --count HEAD 2436; messages with "Co-Authored-By: Claude" 2413). The creator's actions: score/review/__init__.py; his edits recorded with his words: CLAUDE.md "Design edits the owner asks for". -->

# Discussion

The design rests on one observation, that an environment generated step by step, with every step held to a measured gate and keyed on its inputs, can carry its physics and its authorship in the record itself. The consequences of this are concrete, although until environment 1's batch has run they are properties of the design and not yet measured results:

- **Faults have an address.** Because each layer is made by its own node and judged by its own gates, a fault is found at the step that caused it and not in a finished scene, and fixing it moves only the keys downstream of that step. Demonstration 4 is to measure what this saves.
- **One record for many readers.** The physics is written in OpenUSD's physics schema and not in one engine's format, so any reader of that schema obtains the same bodies, joints and gravity. Demonstration 3 is to test this in a game engine, a robot simulator and a film renderer.
- **The creator stays the author.** Every model allows commercial use of its output, every finish traces to the creator's library, and the decisions that shape the result (locks, accepts, rejects and waivers) are his own, recorded with their reasons.
- **Agents are not their own judges.** A coding agent writes code builders and connects tools, but it never decides that its own work is done; that decision belongs to measured gates and, above them, to the creator.

## Limitations

**One creator and no accepted run.** A single creator judges every environment, and he has not yet accepted a run; the method has therefore not yet been shown to produce an environment its maker would ship.

**Closed models.** Nano Banana Pro and Gemini 3.1 Pro draw the concepts and close-ups and read and plan every scene. They are closed and may change or be withdrawn, and replacing them with open models remains to be done.

**Unexercised stages.** The design step, the layers from row kinds, the finish route, the shapes-first loop and the scene tree have not yet carried a scene through a batch. The edit layer is still a slot, the settle, the effects and the sim body are not yet on Newton, and no game engine or robot simulator has yet opened the result.

<!-- Engine: score/adapters/engines ("no game engine yet"). Closed models: score/review/concepts.py, reading.py, plan_writing.py, score/stages/props. Edit layer slot: tools/usd/export.py, tools/usd/test_a_creators_edit_survives_a_regenerated_base.py. -->

# Related work

SCORE sits between three lines of work. World models [@bruce2024genie; @genie3] and 3D environment generators [@wang2025worldgen; @hyworld2] generate an environment in one shot, as frames or as a fused asset, and recent work recovers separate objects from that asset afterwards [@hu2026worldact; @niu2026worldsculpt]; SCORE instead makes every object separately from the start, and writes its body into the record. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] keep scenes explicit through hand-written generators, and SCORE uses their shaders, through ProcFunc [@raistrick2026procfunc], as the base of its surface library, while reading what to build from a creator's concept rather than from a fixed grammar. Coding agents that write scenes as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue; @he2026thinking; @wang2026codeasworlds] are closest in spirit, but the scenes they write often float or come apart [@gao2026codebench3d], they judge their own geometry unreliably [@li2026lego], and on scenes rebuilt from video the strongest model scores 0.91 on static scenes but only 0.67 on dynamic ones [@shen2026codebench4d]. SCORE therefore gives such agents a narrow role, writing builders for the objects other routes fail on, and leaves judgement to measured gates.

<!-- 0.91 and 0.67: arXiv 2610.03715 Section 4.2 (strongest model, static versus dynamic families). Citations checked 2026-10-20 against their arXiv pages. -->

# Future work: people true to the person

The minimal sim body is a starting point, and this section states goals rather than results.

The sim body is to become fully musculoskeletal and true to the individual person, older people and those with a curved spine included, rather than a template body resized to fit. Its joint centres are to come from bone landmarks on its SOMA mesh, followed by its mass, muscles, joint ranges, spine and bone shape, with each input that SOMA lacks marked as assumed and given a range. A full musculoskeletal body with 416 muscles already runs on Newton, but it still drifts 1.5 cm from plain MuJoCo after 300 steps, so Newton is to be validated for bodies before more is built on it. The body's joint angles, and then its joint moments and ground forces, are to be held to OpenCap's LabValidation data.

<!-- Person-true body: issue #56 decisions (owner, 2026-10-27), issue #64 (build order; inputs SOMA lacks marked assumed). 416 muscles and 1.5 cm after 300 steps (MyoFullBody on Newton 1.6.1 SolverMuJoCo after six import fixes): https://github.com/Babon-Innovations-b-v/score/issues/63#issuecomment-6441625310. Newton validated for bodies first: issue #56 decisions. LabValidation licence (Apache-2.0, fetched on demand, never committed): https://github.com/Babon-Innovations-b-v/score/issues/57#issuecomment-6441121325. -->

Motion is to come from the SOMA ecosystem: from video through GEM-X [@gemx], from sentences through Kimodo, and from sequences joined across datasets of both. The terrain a motion implies then becomes a SCORE scene on which a sim body follows the motion, so that the scene keeps the motion without the video and without anything that identifies a person.

Beyond following recorded motion, we intend to train a brain, a model that drives a sim body's muscles so that it moves on its own, including over structures it has never seen. Trained on sim-body data and placed in SCORE's invented worlds, under their own gravity and ground, a brain is to adapt to situations no recording holds. Specialised models, for example for clinical groups, would be trained outside SCORE on data that never enters it. Together these form a data loop: sim bodies moving in synthesised scenes produce data, that data trains better and more specialised brains, and a brain driving a sim body in new scenes produces more data.

<!-- Vision and data loop: issue #56 "Vision (owner, 2026-10-27)" and "Not yet sharp". Motion sources: issue #56 decisions (owner, 2026-10-27). Brain: CONTEXT.md "brain". -->

# Conclusion

Simulable environments have been expensive to make because each object, surface, light, sound and body had to be built and joined by hand, and the generative methods that promise to remove that cost produce frames or fused geometry that a simulator cannot step and a creator cannot fully own. SCORE takes a different route. It builds an environment the way studios build a scene, scene within scene and layer by layer, from a design the creator has locked, with every layer made by a keyed step and held to measured gates, and it writes the result as one OpenUSD record whose physics a simulator steps as written. The next steps are environment 1's batch and its four demonstrations, an engine adapter, the edit layer carried across assemblies, further environments, and open models in place of the closed ones. If an accepted environment confirms that the approach holds, we hope it brings owned, simulable worlds within reach of individual creators, researchers and small teams who could not afford to build them by hand, and gives simulated people a place to move in.

# Author Contributions {-}

[J.P. Kardolus conceived the framework, directed its development, made every design lock, pick and accept, and wrote the paper. Coding agents wrote most of the code and drafted the text under his direction, as disclosed in Section 4.]{.todo}

# Competing Interests {-}

The author is affiliated with Babon Innovations B.V., in whose GitHub organisation SCORE is published under the MIT licence. [The author declares no other competing interests.]{.todo}

# Acknowledgments {-}

We thank the authors and maintainers of the open tools and data this work builds on: OpenUSD [@openusd]; Newton [@newton], Warp [@warp], MuJoCo [@todorov2012mujoco] and MuJoCo Warp [@mujocowarp]; Blender [@blender] and Bullet [@bullet]; Infinigen [@raistrick2023infinigen] and ProcFunc [@raistrick2026procfunc]; SAM 3 [@carion2025sam3], SAM 3D Body [@yang2026sam3dbody] and Pixal3D [@li2026pixal3d]; SOMA [@saito2026soma], Kimodo [@rempe2026kimodo] and GEM-X [@gemx]; MOSS-SoundEffect [@moss2026] and CLAP [@wu2022clap]; and the OpenCap team for the LabValidation data [@uhlrich2023opencap].

# Data Availability {-}

The framework's code, the source of this paper, its PDF and its arXiv tree are public at https://github.com/Babon-Innovations-b-v/score under the MIT licence. The run records from which the paper's numbers are read are in the repository under `paper/evidence/`, and every number in the source carries a comment naming the file, commit or issue comment it is read from. Environment 1's outputs are not yet made and are marked as gaps. OpenCap's LabValidation data (Apache-2.0) is fetched from its own source when needed and is not redistributed here.

<!-- LabValidation licence (Apache-2.0, fetched on demand, never committed): https://github.com/Babon-Innovations-b-v/score/issues/57#issuecomment-6441121325. -->

# References {-}

::: {#refs}
:::
