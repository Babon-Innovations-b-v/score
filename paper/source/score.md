---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 21 October 2026"
abstract: |
  Games, films and robot training need 3D environments that are complete, editable and owned by their creators; world models and one-shot generators give frames no engine opens, or one fused scene without separate objects or clear rights. Studios already build such environments by a standard: scenes layered in OpenUSD, each scene sitting within its parent scene and each department's work on it a layer of its own that can be checked and changed apart from the rest. SCORE builds environments by this convention. The creator decides from the top down: he locks an environment concept (EC), its style and its physics, which holds the scenes and their layering, and then a concept for each scene, in order of parent scene and child scene. The framework makes every layer below with open vision foundation models, procedural tools and coding agents, each layer checked before the next is made. Every model allows commercial use of its output, so the creator stays the author. We describe the framework with its first environment as the worked example; its results are marked gaps until its remake has run. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT license).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main text: the three contributions only (the framework, its stages and gates, the evidence),
    about 4 to 5 pages plus references while gaps are open. The appendix holds only the evidence
    behind a claim the main text makes.
  - Every number is read from a file named in a comment beside it.
  - No demo or result from a lost or rejected run: every figure, table and film of environment 1 is a gap
    box until the remake has made it (owner, 2026-10-21).
  - The walkable reference is one optional step; no result compares it with another model or judges it
    on its own, and its output is credited "Generated using World Labs".
-->

```{=latex}
\makeatletter\def\fps@figure{tp}\makeatother\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.1}
```

::: gap
**Gap: Figure 1, one environment top down.** The EC of environment 1 (its style and its physics), a top scene on its site, a parent scene and its child scenes, and one scene's layers side by side. It waits on the remake's batch.
:::

# Introduction

Interactive 3D environments are the raw material of games, film and embodied AI [@yang2024holodeck], and building one is expensive: every object is modelled, surfaced, placed, given collision, lit and given sound in one style, and the environment stays editable. Generative models promise to take over much of this, but in GDC's 2026 survey 52 percent of game workers thought generative AI was hurting the industry [@gdc2026survey]; a tool for building environments has to leave the result in the creator's hands.

Studios already have a standard for this: OpenUSD [@openusd], the scene description Pixar made for its films. Each artist works in a file of their own, a layer; the layers are stacked in a stated order, so departments work on one scene without editing each other's work, and scenes are assembled from smaller ones by reference. In this convention a scene sits within its parent scene and holds its child scenes, and each department's work on it (layout, set dressing, surfaces, light, effects, motion, sound) is a layer that can be checked and changed apart from the rest. SCORE builds environments by this convention, with the creator deciding and the framework doing the departments' work. The creator locks an environment concept (EC): its style and its physics. The EC holds the scenes and their layering. For each scene a concept is then locked, in order of parent scene and child scene, and from it the framework makes every layer below, each its own OpenUSD layer, checked before the next is made.

<!-- OpenUSD: openusd.org "Introduction to USD" ("Why use USD?": each artist works in their own file, a layer, combined in a strength order without editing another artist's work; "What can USD do?": layers stacked by subLayers, references the primary way to assemble assets into complete scenes), read 2026-10-21. Scene, parent scene, child scene, environment concept (EC), physics: CONTEXT.md, owner 2026-10-21. -->

World models generate an environment as frames [@bruce2024genie; @genie3] that no engine can open. 3D environment generators [@wang2025worldgen; @hyworld2] produce geometry, but mostly as one fused asset, from which separate objects are recovered after the fact [@hu2026worldact; @niu2026worldsculpt]. Both work in one shot, so a creator cannot find or change the step behind a fault. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] and coding agents that write scenes as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue; @he2026thinking; @wang2026codeasworlds] keep the environment explicit, but rebuild a scene that already exists or draw their objects from a fixed library; their models often float or come apart [@gao2026codebench3d], and such agents judge their own geometry unreliably [@li2026lego]; on scenes rebuilt from video, the best model scores 0.91 on static scenes but 0.67 on dynamic ones [@shen2026codebench4d], which is why SCORE checks motion as a layer of its own. Open vision foundation models [@oquab2023dinov2] now read shapes [@li2026pixal3d], masks [@carion2025sam3], depth [@wang2025moge2] and parts [@lin2025partcrafter] out of pictures, and a coding agent can connect them as tools; none of them provides one style across objects that different models made, which the field names as an open problem [@wu2026production; @yang2026flowscene].

<!-- 0.91 and 0.67: arXiv 2610.03715 Section 4.2 (strongest model, static versus dynamic families). Citations checked 2026-10-20 against their arXiv pages. -->

SCORE's environments are meant to be **complete**: every object, surface, light and sound exists wherever the viewer looks. They are **owned**: every model in the framework allows commercial use of its output, so the creator stays the author, holding the full commercial rights. They are meant to be **responsive**: every object has real collision, mass and material. And they can be any kind of **environment**, from a house on a plot of ground to a system of worlds. To our knowledge, no other openly available environment generation work joins vision foundation models into engine-ready environments that are built from reference pictures, steered by a person's choices at each step, and made only with models that allow commercial use of their output.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Scales of an environment: CONTEXT.md "physics" (owner 2026-10-21). -->

We contribute **the SCORE framework**, which builds an environment by the studios' convention, the creator deciding top down and the framework making every layer below (Section 2); **measured gates** for every layer of a scene and a completion gate over them (Section 3); and **evidence from a first environment**, left as gaps until its remake has run (Section 4).

# The framework

The creator works in the creator cockpit, one signed-in web page: there he decides the design, buys paid work and reviews what the framework reports. Below him, an environment is a table of stages read off its designs; environment 1's has 261 rows today, 201 of them the bodies of the 67 people its designs show. A **node** is one stage for one scene (`assembly@hangar`) or for the environment, and one runner makes, judges and accepts every node. From an approved design everything runs without a further yes.

<!-- 261 rows, 201 of them people-look-parts-, people-body- and people-dress- rows (three a look): len(score.stages.STAGES) at 68378cc4. The cockpit: CONTEXT.md "creator cockpit"; score/dashboard. Design before the batch: owner 2026-10-20, issue #10 comment 2026-10-20T18:00:28Z. -->

## Keys, gates and accepts

**Keys.** A node is made only when its key has no finish record. The key hashes the stage and scene, its code version, contracts, parameters and seed, the pinned model images, every file it reads and the accepted output of every node it reads. A fault fixed in one stage moves only its key and those after it. Outputs are kept by content hash, never overwritten.

**Gates and accepts.** Each gate answers pass, fail or unknown, with measures and a reason; missing evidence is unknown, and unknown blocks like fail. The runner accepts an output by itself when every gate passed and it is no worse than the one accepted before: no answer dropped, no measure moved the wrong way by a step a viewer could see, no gate missing. Later nodes read only accepted outputs. The creator keeps four actions, buttons in the cockpit: reject an accepted output (it moves back to the one before, and every node that read it is stale), accept a worse one with a reason, waive one gate for one key, and override the runner for one paid run. A barrier keeps agents from them: a store that refuses the creator's records from an agent's process, and a hook.

**Batches.** Paid work is bought as a batch, with one estimate and one ETA; the creator's yes to that estimate is the only spend decision, and the batch stops at its high estimate plus 10 percent. A scene enters a batch only once its design stands whole on its lock, and Buy waits until the film script is locked. Inside a batch every paid job runs once, with no retry; a failed output becomes a batch gap that the completion gate lists, and spending more on it is a new batch. The creator reviews each scene in a 3D viewer on its accepted assembly.

<!-- Keys: score/graph/__init__.py (own_parts, worked_out_key, node_seed, code, usable), score/graph/_code.py (source_files, FRAMEWORK). Contracts and store: score/contracts, score/store. Gates: score/checks (judge, missing_evidence, overall, blocks, regressions). Accepts and the creator's actions: score/review/__init__.py (accept_automatically, accept, reject, waive), the cockpit's buttons applied by the sync pass on the owner's PC (score.review.web, #39), score/store OWNER_AREAS, .claude/hooks/accept_guard.py. Batches: CONTEXT.md "batch" (owner 2026-10-20); the stop: score/dashboard/checkout/flow.py BUFFER = 1.10; Buy waits: commits 4aaa54c4 (design whole), 8c89174a (film script locked); batch gaps: score/stages/batch_gaps.py, commit 1b61643d. -->

## From concept to scene

**The environment concept.** The creator first locks the EC, in a short interview with Gemini 3.1 Pro [@gemini31pro] in the cockpit: its style and its **physics**, with his reference pictures. The EC holds the scenes and their layering: the top scenes and the child scenes each may hold. Its physics is what everything stands on and in and how it moves, at the scale he sets: a plot of ground with a gravity and a sun path, one world, or a system of bodies that move one another, a real body taking its values from a cited table and an invented one given by its radius, mass, orbit and spin. A body near enough to matter moves in the physics simulation, a far source of light is a light, and what is too far to move is a backdrop. An environment plan places each top scene's site on that ground, shaped by that scene's own plan, and works out the sky each site sees.

**A concept for each scene, top down.** For each scene a concept is then locked, in order of parent scene and child scene. Each draw is one Nano Banana Pro [@nanobananapro] call that the creator's click pays for, on a concept review page where he marks areas and asks for a new draw, or first discusses the draw with Gemini 3.1 Pro, the thread going with his next draw. A child scene is drawn only once its parent scene is locked and planned, on a crop of the parent's concept, so it fits the parent it stands in.

**Inventory and plan.** The creator's lock is the approval. Gemini 3.1 Pro lists every object of the locked concept as a row of the scene inventory, with its kind, count, anchor and size in metres, and SAM 3 [@carion2025sam3] boxes each row on the concept. A row counts when both find it, or when Gemini names one large object (at least 2 percent of the picture) that SAM 3 misses, boxed by Gemini's region; a row without metres is a gap. Nothing is made or placed that is not a row. The plan is made in two calls. Nano Banana Pro first draws the scene from straight above, from the locked concept, in the frame of the scene's own proportions; Gemini 3.1 Pro then writes the plan in metres from that drawing, the concept and the inventory, element by element: outline, walls, openings, levels, stairs, roofs, terrain heights, each item with its facing, people as the spots they stand on, and the child scenes' rooms. Free checks follow (every row placed as often as it counts, inside the outline, no two floor items in each other, each item placed and facing as in the concept, every door and standing spot reached on foot, the child scenes tiling their parent). What code can settle is fixed before the plan is shown, what remains goes back to Gemini 3.1 Pro as notes at most twice, and only what is left is a gap. A plan the creator drew himself wins over a written one, and his edits on the plan review page always win and redo what follows: he moves and resizes rooms, and a box he drops wholly inside a room is a thing in it, one dropped over another room makes the two one shared room, and one dropped anywhere else is a new child scene. A child scene he has locked keeps its room when its parent's plan is written again. Only a scene with a design gets the rows of a batch.

<!-- Discuss: score/review/discuss.py, commit 3faf81b9. Drop rule: commit d55fa04b (plan.js; plans.checked_hold, checked_thing). Large single object (2 percent, Gemini's region): score/review/reading.py, commit 36653107. Top-down drawing then the plan: score/review/plan_drawing.py, plan_writing.py. Checks and the fix step (at most two notes rounds): score/review/plan_checks, plan_fixes.py, commit dcc9bb14. His plan wins, his edits shown, locked children keep their rooms: score/review/plans.py, commits 2604f113, d307de88. -->

<!-- CONTEXT.md: environment concept, physics, environment plan, design, concept review, plan review, scene inventory (owner 2026-10-20 and 2026-10-21). Code: score/review/environment_concept.py (interview, Gemini 3.1 Pro), setting.py (data/physics/bodies.json, the cited table), environment_plan.py (each site's shape read from its scene's plan), sky.py, concepts.py (draws, locks), reading.py (MODEL gemini-3.1-pro-preview; SAM 3 boxes), plan_writing.py, plan_checks.py (placed, outside, overlap, reach, tiling), plans.py; commits 760f02c7, 2d38b67b, d7e13db6. Design gating: score/stages/complete/prepare/handin.py, commit f8ae4081. -->

**Shapes first.** The route is one loop, the same at every scale. A parent scene gets its concept, its plan and a rough model, its concept put through picture to 3D whole, which gives the plan its proportions. Its plan is then split into the shapes of its child scenes, and once those shapes are fixed every child scene is made in parallel, each repeating the loop (the creator's order of 19 October 2026). The runner's rows `rough-model` and `shell-split` (gated on `tiled`, `reached` and `bounded`) are built and have not run.

<!-- The creator's order: owner, 2026-10-19, issues #10 and #11. Rows: score/stages/rough_model (#15), score/stages/shell_split (#16). No run: paper/evidence/design/design-2026-10-21.txt (rough-model and shell-split records: 0). -->

**The scene record.** The scene record holds what no made piece covers (shells, stairs, ground and water, backdrop, lamps, the neighbours a scene shows), written from the plan, inventory and made ground, and gated on `game-free`, `plan-matched` (the shell within 5 cm of the plan) and `openings` (every doorway onto a floor, no view into nothing).

**The canonical scene.** Every scene is one OpenUSD stage [@openusd]; each object, one per real-world object, carries its kind, transform, collision and each part's library surface. Its layers are read off its design alone: each inventory row's kind, found free from the reading's noun, says what its objects do (emit, move, lie loose, glow, grow, act, sound), a scene gets an effects, motion, physics, crops or people layer only for rows that do so, and light and sound always. Each layer is made from the rows by their kind's rule, never from a record written for one scene, so a new environment needs no hand-written list. The layers stack in a fixed order: a slot for the creator's edit layer on top, then people, sound, light, motion, effects, crops, machines, settle, ground and the base, laid from the locked plan. Each scene is assembled once from every layer's accepted output; its `layers` gate answers unknown while a layer its design shows has none. Walls, floors, stairs and ground collide and every model has a collider (`collision`); colliders are static, mass and interaction not yet written. **A parent scene holds its child scenes**: its scene tree references each child's own tree at the room its plan gives it, so opening a top scene opens all below it, each still its own layer stack (`child scenes`). Neighbours are referenced the same way; a shown scene no stage makes is a gap. The edit layer is still a slot: a test on a two-box scene shows an edit there surviving a regenerated base, but the assembly does not yet carry the creator's edits from one assembly to the next.

<!-- Inventory rule: the owner's rule of 2026-10-08. Plan and record: score/stages/scene_record (plan.py: mapped; gates.py: game-free, plan-matched, openings, TOLERANCE = 0.05; seed-matched retired with the old records, commit b0af8477). Row kinds: score/stages/row_kinds.py, data/checks/row-kinds.json (19 kinds), score/stages/design_layers.py (DOES, EVERY_SCENE), commits be088c14, 99d19861, d8012846. Base from the design: score/stages/earth_seed, commit e71a41a8. Layer order: score/stages/assembly/record.py ORDER; layers gate: judge_layers; collision: score/stages/assembly/__init__.py judge_collision, tools/usd/colliders.py, commits 29d821d3, 7abaa095. Scene tree: score/stages/assembly/scene_tree.py, commit 8f07a249. Neighbours: score/stages/assembly/neighbours.py, commit 29de1b39. The edit layer: tools/usd/export.py and its test tools/usd/export_test.py (two boxes). -->

**Models, generation first.** Every object goes the prop route first: Nano Banana Pro draws its close-up once from its crop of the concept, Pixal3D [@li2026pixal3d] builds it, the surface stage paints it, and a likeness gate compares its outline from eight sides with its close-up. A close-up that fails the shape check is a batch gap, so Pixal3D is never paid for it. Only an object whose checks fail is built by a code builder a coding agent writes (the creator's choice, 12 October 2026). A big object the viewer walks up to gets a body built in code under the generated details its entry names (the creator, 18 October 2026).

<!-- Prop route first: score/stages/props/CLAUDE.md (owner 2026-10-12). One close-up an object: tools/props/closeup/stage.py PRO_TAKES = ("pro",), score/stages/props/closeup_row.py. Likeness: likeness.py (eight outlines, OUTLINE_LEAST = 0.50). Bodies: tools/props/library/CLAUDE.md (owner 2026-10-18), tools/props/library/inside/bodies.py. -->

::: gap
**Gap: Figures 2 and 3.** (2) One scene's design top down: the EC, the parent scene's concept and plan, a child scene drawn on its parent's crop, its inventory and plan. (3) Objects of one scene from close-up to final model, generated and code-built. They wait on the remake's designs and batch.
:::

# Stages and their gates

## Surfaces: the finish route

Everything a scene shows comes from the creator's library, score_lib, or is a written exception (the creator's rule of 18 October 2026). Models give shape only: a picture-made model keeps its geometry and its finish is replaced. Every part takes one surface from a shared library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen], coloured from the scene's palette and worn only where wear has a cause. The library starts empty for the remake: every surface and model of the earlier runs was retired on 21 October 2026, so the batch makes them fresh. Each scene's palette is coined from its locked concept, one Gemini 3.1 Pro batch answer gives its surfaces as settings of the recipes, and an entry is reused only when made under today's route.

The finish route gives each model its finishes (the creator's choice of 20 October 2026). Free renders cover every face of the raw model, each view split into colour regions; one Gemini 3.1 Pro answer a model lists its finishes, each matched to a library surface, and labels each region, and the labels vote across views into one finish a face, a face no label reaches or whose views disagree being a gap. Each part is painted from its library surface and baked, and the bake is checked against the close-up: a finish's surface must lie within ΔE 32 of its colour there, a bake fails when it darkens a finish the close-up shows lighter or turns all surfaces into one grey, and a foot over 3 cm off the floor fails. A free library check traces every material, model, light, sound and character of a scene's accepted assembly to a library entry or a written exception.

<!-- The empty library: commits 143324a6 (surfaces; finish-route-palette coins tokens, surface-library@<scene> in score/stages/surfaces/scene_library.py), 3a927ab1 (models and sounds); reuse under today's route: score/stages/complete/prepare/library.py, docs/bible.md architecture/components. The library rule: the owner's hard rule of 2026-10-18, commit 4c8d3b4d; docs/bible.md architecture/components; exceptions: data/checks/library-exceptions.json; the check: score/stages/complete/library. Finish route: score/stages/surfaces/CLAUDE.md (owner 2026-10-20, #18; rows finish-route-views, -list, -split, surfaces-parts, -bake, -paint, finish-route-recheck, surfaces-check; VIEW_DELTA_E 32), commit 5c1e82b6. Bake checks: bake_check.py (BAKE_DELTA_E 20.0, CLOSE_UP_DELTA_E 32.0, order_faults, one_look_faults); feet: tools/props/library/feet.py. -->

## Resting

Loose objects are dropped onto the made ground in a physics simulation; one that would turn more than 15 degrees or drift more than 30 cm is a resting fault of the layout and keeps its laid pose. The settle stage lays where each object comes to rest as a layer (held objects snapped onto their holders, a stack onto one support, an object that would rest worse kept as laid), gated on `rested` and `resting` (no fault that appears with the layer and not without it). A physics layer writes the scene's physics in OpenUSD, and a trial on Bullet drops the loose rows' objects where they stand, under the gravity of the body the scene stands on (`reacted`, `at rest`, `energy`, `hinge`).

<!-- tools/usd/settle.py TURN_MOST 15, DRIFT_MOST 0.3; score/stages/settling (held.py, onto_one_support, kept_where_worse; gates rested, resting). Physics: score/stages/physics (design.py; gates laid, designed, reacted, hinge, at rest, energy), its overlay; commits da1b6fce, 50c41a8e. -->

## Light

The sky is worked out from the EC's physics, never drawn: the light layer writes what the scene's top site sees overhead at its scene time, each body at its true direction, size and phase (`sky bodies`), and a light under the horizon lights nothing. The lamps are the inventory's glowing rows, and their strengths are measured. One paid render per scene gives every lamp its own Cycles light group on the scene's views; because light adds up, the look at any strengths is mixed from these passes without rendering again, and a free sweep chooses the scale that brings the scene's brightness within 1.5 times its concept's, halving any lamp that turns what it lights white.

<!-- Sky: score/review/overhead.py, scene_sky.py, score/stages/light/sky.py (gate sky bodies; risen), commits 1fdd838e, 858c8c57. Lamps: commits 96db9bf0, 2fefc1ae (glowing rows, data/library/lamps.json). score/stages/light: mix.py (BRIGHT_WITHIN 1.5, BLOWN_MOST 0.2, HALVINGS 5), layer.py, gates in __init__.py; score/stages/light/CLAUDE.md. -->

## Motion, effects and sound

**Motion.** Every object of a moving row moves by its kind's rule (a door swings and shuts, a crane slews, a fan spins) at the middle of its kind's speed range cited from real machines, gated on `clear` (no moving thing within 3 cm of a still thing or another moving thing, read every quarter second), `speeds`, `loops`, `grounded`, `covered` and `designed`. **Effects:** an emitting row's objects carry their kind's emitters, measured against real footage, gated on `attached`, `footage`, `light`, `outside` (no open-sky particle inside a room) and `designed`. **Sound:** a scene's sources come from its design (a bed from how the scene is heard, its sounding rows, its people's voices and its moving things), and each gets a library file or one MOSS-SoundEffect [@moss2026] take of its brief, gated on `sources`, `bed`, `events`, `voices`, `level`, `likeness` (CLAP [@wu2022clap] score at least 0.30; a take under it is a gap) and `no freesound`.

<!-- Motion: CONTEXT.md "motion" (owner 2026-10-20, 2026-10-21); score/stages/motion (from_design.py), tools/usd/motion_layer.py, data/checks/motion.json (speed ranges, cited), REACH_MOST 0.03; the old records and motion-models retired, commits c3ef49db, dd69d068. Effects: score/stages/effects (from_design.py), data/checks/effects.json; effects-look retired, commit dd69d068. Sound: score/stages/sound (beds.py, its overlay; commits 0d0dad26, 56b50f79, 5b6e623e; gates.py CLAP_FLOOR 0.30; takes.py: one take a brief; commit 8895484d). -->

## People

People are models like any other. The looks come from the person rows of the locked designs, each person from its own SAM 3 box on the concept and a crowd as one far look; the shared loop draws its close-up (one person, front on, in the rig's A-pose), Pixal3D builds it and the finish route paints it. The rigged body takes each part's library surface from that paint, its face and hair included, and the library surfaces are baked onto the body itself as onto any model and checked the same way; no picture's finish reaches it. SOMA-X's body, read from the close-up by SAM 3D Body [@yang2026sam3dbody], is fitted under it as its rig, and Kimodo's clips [@rempe2026kimodo], from sentences, move it. The **shell gate** passes a look when 99 percent of its soft points lie within 5 cm of the body, its worst point recorded; each clip gets its own verdict, and casts use only passing clips. **Casts:** each person stands on a person spot of its scene's plan, gated on `counted`, `standing`, `clear` and `made`.

<!-- score/stages/people/CLAUDE.md (the shared loop, the PERSON close-up wording of tools/props/closeup/stage.py); the body's finish: score/stages/people/dress.py, baked_body.py, inside/bake_body.py (owner 2026-10-23, #26); score/stages/people_bodies/bodies.py (SAM 3D Body's read; SHELL_SHARE 0.99, OFFSET_MOST 0.05), clips.py, far.py; score/stages/people_rows.py (commits de320cb2, c5f14fea); the old makes, garment designs and person chain retired, commit 37b54b3b; score/stages/cast (gates counted, standing, clear, made); CONTEXT.md "cast" (#26). -->

## Completion

A scene is complete when its gate passes on its final assembly: every row made or dropped with a reason, nothing unmade, no placeholder or resting fault, the creator's picks shown and every layer and shown scene present. A fault the creator decides to ship with is an accepted gap, written with who decided, when, why and its measured faults; the completion gate lists every gap by name and is never loosened, and a scene whose accepted gaps are its only fail is complete apart from accepted gaps. A hook stops an agent claiming a scene is done while its gate fails: agents judging their own scenes agree with a measured geometry score only 45.8 percent of the time [@li2026lego].

<!-- Accepted gaps: score/stages/gaps.py, data/checks/gaps/<place>.json; batch gaps: score/stages/batch_gaps.py. tools/usd/complete.py CHECKS; tools/usd/contents.py JUDGES; score/stages/complete; .claude/hooks/completion_guard.py. LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. -->

## The film

The film is a design step too: the creator locks a film script in the cockpit (by default the whole environment, body by body), and a scene's films are made from locked scripts only, once it is complete or complete apart from accepted gaps.

<!-- score/stages/demo_film (its overlay: films from the locked scripts, made once complete passes or fails only on accepted gaps); score/dashboard/films (default.py); commits 8c89174a, fe4c675d, 22d0d649. -->

::: gap
**Gap: Figures 4 to 7.** (4) A scene's models painted from the library beside their close-ups; (5) a scene swept to its concept's light; (6) motion and effects in place; (7) its people and their cast. They wait on the remake's assemblies.
:::

## Prices and ledgers

Every paid stage is priced from a unit cost measured on the ledgers, times the units its forecast rule counts, times the bill's share over the ledger; a stage with no measured run has no price, and its estimate is shown apart as a guess. Today 15 of the table's 29 paid kinds of row have a measured unit price, four of them from two benchmark batches of 21 October 2026 that the creator approved, one node a kind. Machines and Google calls write ledger lines with their node's clearance, and the month's spend is the higher of ledgers and bill, which caught misses: EUR 1,554 billed against EUR 1,387 in the cloud ledger on 12 October 2026. A paid node runs only when every gate on its inputs passed, the month's books are known and its batch's stop has room for its forecast.

<!-- Bill against ledger: tools/props/cloud/CLAUDE.md (bill EUR 1,554 vs ledger 1,387 on 2026-10-12). Unit prices: data/costs/per-unit.json (17 stages, 15 of them rows of the table at 68378cc4, whose paid rows are 29 kinds; finish-route-palette, surface-tiles and people-clips-made under grant 20261021T182203, commit f91dcf9c; library-clips under grant 20261020T224639, run 2026-10-21), tools/costs/per_unit.py; bill share: compute.bill_share (ADR-0006); guesses kept apart: score/adapters/compute run_price (guess_euros). Clearance: score/adapters/compute/__init__.py (clearance, books_refusal, require_cleared). -->

# Evidence

Environment 1 is the worked example. Its first run was not accepted by the creator and its store was lost on 19 October 2026, so this draft shows none of its outputs; its remake from new designs has not run.

<!-- The creator's review: issue #10 body. The loss: docs/bible.md architecture/failure ("Losing $PROPS_HOME", 2026-10-19, #13). -->

::: gap
**Gap: Table 1 and the film.** Per scene of the remake: inventory rows, models generated and coded, layers, gaps before and after the batch, time, euros and the creator's verdict; and a walk through environment 1. They wait on the remake's batch and the creator's review.
:::

::: gap
**Gap: Table 2, people.** Usable clips per look by the shell and clip gates on the remake's people. It waits on the people line's batch.
:::

**Agent tools.** With them an agent used about half the output and cost on two of three scenes; on the third it left more faults; one run each.

<!-- paper/evidence/agent-tools-bench/analysis.json; the details in paper/source/notes.md "With and without the agent tools" (not printed). -->

# Limitations, future work and conclusion

One creator judges, and he has not yet accepted a run. Closed models (Nano Banana Pro, Gemini 3.1 Pro) draw the concepts and close-ups and read and plan every scene; they may change or go. The design step, the layers made from row kinds, the fresh library, the finish route, the shapes-first loop, the scene tree and the code bodies have not yet carried a scene through a batch; the edit layer is a slot, colliders are static and objects are not interactive, and no game engine opens the result yet. Next: the remake's batch, an engine adapter with physics and interaction, an edit layer the assembly carries, three more environments, open models, LEGO-Bench [@li2026lego]. In short, SCORE builds an environment the way studios do, scene by scene and layer by layer, so a fault is fixed in its own layer; an accepted environment will show if it holds.

<!-- Engine: score/adapters/engines ("no game engine yet"). Closed models: score/review/concepts.py (Nano Banana Pro draws), reading.py and plan_writing.py (Gemini 3.1 Pro), score/stages/props (close-ups by Nano Banana Pro). -->

# References {-}

::: {#refs}
:::
