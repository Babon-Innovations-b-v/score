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

The creator works in the creator cockpit, one signed-in web page: there he decides the design, buys paid work and reviews what the framework reports. Below him, an environment is a table of stages; environment 1's has 149 rows. A **node** is one stage for one scene (`assembly@hangar`) or for the environment, and one runner makes, judges and accepts every node. From an approved design everything runs without a further yes.

<!-- 149 rows: len(score.stages.STAGES) at b205e997. The cockpit: CONTEXT.md "creator cockpit"; score/dashboard. Design before the batch: owner 2026-10-20, issue #10 comment 2026-10-20T18:00:28Z. -->

## Keys, gates and accepts

**Keys.** A node is made only when its key has no finish record. The key hashes the stage and scene, a code version, the contracts of its output and inputs, its parameters, a seed derived from the environment's, the pinned model images, every environment file it reads and the accepted output of every node it reads. A fault fixed in one stage moves only its key and those after it. Outputs are kept by content hash, never overwritten.

**Gates and accepts.** Each gate answers pass, fail or unknown, with measures and a reason; missing evidence is unknown, and unknown blocks like fail. The runner accepts an output by itself when every gate passed and it is no worse than the one accepted before: no answer dropped, no measure moved the wrong way by a step a viewer could see, no gate missing. Later nodes read only accepted outputs. The creator keeps four actions, buttons in the cockpit: reject an accepted output (it moves back to the one before, and every node that read it is stale), accept a worse one with a reason, waive one gate for one key, and override the runner for one paid run. A barrier keeps agents from them: a store that refuses the creator's records from an agent's process, and a hook.

**Batches.** Paid work is bought as a batch, with one estimate and one ETA; the creator's yes to that estimate is the only spend decision, and the batch stops at its high estimate plus 10 percent. Inside a batch every paid job runs once, with no retry; a failed output becomes a batch gap that the completion gate lists, and spending more on it is a new batch. Each node's review page is built from the store alone, and the creator reviews a scene in a 3D viewer on the store's copy of its accepted assembly.

<!-- Keys: score/graph/__init__.py (own_parts, worked_out_key, node_seed, code, usable), score/graph/_code.py (source_files, FRAMEWORK). Contracts and store: score/contracts, score/store. Gates: score/checks (judge, missing_evidence, overall, blocks, regressions). Accepts and the creator's actions: score/review/__init__.py (accept_automatically, accept, reject, waive), the cockpit's buttons applied by the sync pass on the owner's PC (score.review.web, #39), score/store OWNER_AREAS, .claude/hooks/accept_guard.py. Batches: CONTEXT.md "batch" (owner 2026-10-20); the stop: score/dashboard/checkout/flow.py BUFFER = 1.10; batch gaps: score/stages/batch_gaps.py, commit 1b61643d. -->

## From concept to scene

**The environment concept.** The creator first locks the EC, in a short interview with Gemini 3.1 Pro [@gemini31pro] in the cockpit: its style and its **physics**, with his reference pictures. The EC holds the scenes and their layering: the top scenes and the child scenes each may hold. Its physics is what everything stands on and in and how it moves, at the scale he sets: a plot of ground with a gravity and a sun path, one world, or a system of bodies that move one another, a real body taking its values from a cited table and an invented one given by its radius, mass, orbit and spin. A body near enough to matter moves in the physics simulation, a far source of light is a light, and what is too far to move is a backdrop. An environment plan places each top scene's site on that ground at true size and works out the sky each site sees.

**A concept for each scene, top down.** For each scene a concept is then locked, in order of parent scene and child scene. Each draw is one Nano Banana Pro [@nanobananapro] call that the creator's click pays for, on a concept review page where he marks areas and asks for a new draw. Every draw is sent a **blockout** first, a grey model built in code from the parent's plan at real sizes, so it keeps that layout and proportions and adds the look. A child scene is drawn only once its parent scene is picked and planned, on a crop of the parent's concept, so it fits the parent it stands in.

**Inventory and plan.** The creator's pick is the approval. Gemini 3.1 Pro lists every object of the picked concept as a row of the scene inventory, with its kind, count, anchor and size in metres, and SAM 3 [@carion2025sam3] boxes each row on the concept; a row without metres, or a disagreement between the two, is a gap. Nothing is made or placed that is not a row. One more Gemini 3.1 Pro call writes the plan in metres, element by element: outline, walls, openings, levels, stairs, roofs, terrain heights and each item. Free checks follow: every row placed as often as it counts, inside the outline, no two floor items in each other, every door and standing spot reached on foot, and the child scenes tiling their parent. On the plan review page the creator corrects the plan, and his edits redo what follows. Only a scene with a design gets the rows of a batch.

<!-- CONTEXT.md: environment concept, physics, environment plan, blockout, design, concept review, plan review, scene inventory (owner 2026-10-20 and 2026-10-21). Code: score/review/environment_concept.py (interview, Gemini 3.1 Pro), setting.py (data/physics/bodies.json, the cited table), environment_plan.py, sky.py, blockout.py, concepts.py (draws, picks), reading.py (MODEL gemini-3.1-pro-preview; SAM 3 boxes), plan_writing.py, plan_checks.py (placed, outside, overlap, reach, tiling), plans.py; commits 760f02c7, 2d38b67b, d7e13db6. Design gating: score/stages/complete/prepare/handin.py, commit f8ae4081. -->

**Shapes first.** The route is one loop, the same at every scale. A parent scene gets its concept, its plan and a rough model, its concept put through picture to 3D whole, which gives the plan its proportions. Its plan is then split into the shapes of its child scenes, and once those shapes are fixed every child scene is made in parallel, each repeating the loop (the creator's order of 19 October 2026). The runner's rows `rough-model` and `shell-split` (gated on `tiled`, `reached` and `bounded`) are built and have not run.

<!-- The creator's order: owner, 2026-10-19, issues #10 and #11. Rows: score/stages/rough_model (#15), score/stages/shell_split (#16). No run: paper/evidence/design/design-2026-10-21.txt (rough-model and shell-split records: 0). -->

**The scene record.** The scene record holds what no made piece covers (shells, stairs, ground and water, backdrop, lights, sky, the neighbours a scene shows), written from the plan, inventory, made ground and sky, and gated on `plan-matched` (the shell within 5 cm of the plan), `openings` (every doorway onto a floor, no view into nothing) and `seed-matched` (every old entry matched or dropped with a reason).

**The canonical scene.** Every scene is one OpenUSD stage [@openusd]; each object, one per real-world object, carries its kind, transform, collision and each part's library surface. Each department's work is a layer, in a fixed order: a slot for the creator's edit layer on top, then people, sound, light, motion, effects, crops, machines, settle, ground and the generated base. Each scene is assembled once, from every layer's accepted output; its `layers` gate answers unknown while a needed layer has none, and an old output never stands in. A scene shows its neighbours by reference to their own accepted assemblies. The edit layer is still a slot: a test on a two-box scene shows an edit there surviving a regenerated base, but the assembly does not yet carry the creator's edits from one assembly to the next.

<!-- Inventory rule: the owner's rule of 2026-10-08. Plan and record: score/stages/scene_record (plan.py: mapped; gates.py: game-free, plan-matched, openings, seed-matched, TOLERANCE = 0.05). Layer order: score/stages/assembly/record.py ORDER; the edit layer: tools/usd/export.py and its test tools/usd/export_test.py (two boxes); layers gate: judge_layers. Neighbours: score/stages/assembly/neighbours.py (references to each neighbour's accepted assembly; docs/bible.md architecture/components). -->

**Models, generation first.** Every object goes the prop route first: Nano Banana Pro draws its close-up once from its crop of the concept, Pixal3D [@li2026pixal3d] builds it, the surface stage paints it, and a likeness gate compares its outline from eight sides with its close-up. A close-up that fails the shape check is a batch gap, so Pixal3D is never paid for it. Only an object whose checks fail is built by a code builder a coding agent writes (the creator's choice, 12 October 2026). A big object the viewer walks up to gets a body built in code under the generated details its entry names (the creator, 18 October 2026).

<!-- Prop route first: score/stages/props/CLAUDE.md (owner 2026-10-12). One close-up an object: tools/props/closeup/stage.py PRO_TAKES = ("pro",), score/stages/props/closeup_row.py. Likeness: likeness.py (eight outlines, OUTLINE_LEAST = 0.50). Bodies: tools/props/library/CLAUDE.md (owner 2026-10-18), tools/props/library/inside/bodies.py. -->

::: gap
**Gap: Figures 2 and 3.** (2) One scene's design top down: the EC, the parent scene's concept and plan, a child scene drawn on its blockout, its inventory and plan. (3) Objects of one scene from close-up to final model, generated and code-built. They wait on the remake's designs and batch.
:::

# Stages and their gates

## Surfaces: the finish route

Everything a scene shows comes from the creator's library, score_lib, or is a written exception (the creator's rule of 18 October 2026). Models give shape only: a picture-made model keeps its geometry and its finish is replaced. Every part takes one surface from a shared library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen], coloured from the scene's palette and worn only where wear has a cause (Appendix D).

The finish route gives each model its finishes (the creator's choice of 20 October 2026). Free renders cover every face of the raw model, and each view is split into colour regions. One Gemini 3.1 Pro answer a model lists its finishes, each matched first to a library surface with its settings, and labels each region of each view; the labels vote across views into one finish a face, and a face no label reaches or whose views disagree is a gap. Each part is painted from its library surface and baked, and the bake is checked against the close-up: a finish's surface must lie within ΔE 32 of its colour there, a bake fails when it darkens a finish the close-up shows lighter or turns all surfaces into one grey, and a foot over 3 cm off the floor fails. A free library check traces every material, model, light, sound and character of a scene's accepted assembly to a library entry or a written exception.

<!-- The library rule: the owner's hard rule of 2026-10-18, commit 4c8d3b4d; docs/bible.md architecture/components; exceptions: data/checks/library-exceptions.json; the check: score/stages/complete/library. Finish route: score/stages/surfaces/CLAUDE.md (owner 2026-10-20, #18; rows finish-route-views, -list, -split, surfaces-parts, -bake, -paint, finish-route-recheck, surfaces-check; VIEW_DELTA_E 32), commit 5c1e82b6. Bake checks: bake_check.py (BAKE_DELTA_E 20.0, CLOSE_UP_DELTA_E 32.0, order_faults, one_look_faults); feet: tools/props/library/feet.py. -->

## Resting

Loose objects are dropped onto the made ground in a physics simulation; one that would turn more than 15 degrees or drift more than 30 cm is a resting fault of the layout and keeps its laid pose. The settle stage lays where each object comes to rest as a layer (held objects snapped onto their holders, a stack onto one support, an object that would rest worse kept as laid), gated on `rested` and `resting` (no fault that appears with the layer and not without it).

<!-- tools/usd/settle.py TURN_MOST 15, DRIFT_MOST 0.3; score/stages/settling (held.py, onto_one_support, kept_where_worse; gates rested, resting). -->

## Light

Lamp strengths are measured. The light layer places live lamps from the scene record, with the sky and its bodies. One paid render per scene gives every lamp its own Cycles light group on the scene's views; because light adds up, the look at any strengths is mixed from these passes without rendering again, and a free sweep chooses the scale that brings the scene's brightness within 1.5 times its concept's, halving any lamp that turns what it lights white.

<!-- score/stages/light: mix.py (BRIGHT_WITHIN 1.5, BLOWN_MOST 0.2, HALVINGS 5), layer.py, gates in __init__.py; score/stages/light/CLAUDE.md. -->

## Motion, effects and sound

**Motion.** Each moving thing (a path, a hinge, a spin, a rail, a turn, a climb) has its kind's speed range cited from real machines, gated on `clear` (no moving thing within 3 cm of a still thing or another moving thing, read every quarter second), `speeds`, `loops`, `grounded` and `covered`. **Effects** are emitters measured against real footage, gated on `attached`, `footage`, `light` and `outside` (no open-sky particle inside a room). **Sound:** every source a scene names gets the environment's picked file or one MOSS-SoundEffect [@moss2026] take of its brief, gated on `sources`, `level`, `likeness` (CLAP [@wu2022clap] score at least 0.30; a take under it is a gap) and `no freesound`.

<!-- Motion: CONTEXT.md "motion" (owner 2026-10-20, 2026-10-21); score/stages/motion, tools/usd/motion_layer.py, data/checks/motion.json (speed ranges, cited), REACH_MOST 0.03. Effects: score/stages/effects, data/effects/*.json. Sound: score/stages/sound (gates.py CLAP_FLOOR 0.30; takes.py: one take a brief; commit 8895484d). -->

## People

People are made like props: a FLUX.2 klein [@flux2klein] close-up in SOMA-X's bind pose, built by Pixal3D, painted by the surface line, over SOMA-X's body fitted just inside, whose skin weights each look point takes from its closest triangle; Kimodo's clips [@rempe2026kimodo], from sentences, move it. The **shell gate** passes a look when 99 percent of its soft points lie within 5 cm of the body, its worst point recorded; each clip gets its own verdict (tucks, hard parts stretched, cloth or body through cloth), and casts use only passing clips. **Casts:** each person of a scene's inventory is a look of the people line, SAM 3 finds the concept's figures, and casts are gated on `counted`, `standing`, `clear`, `made` and `drapes`.

<!-- score/stages/people_bodies/bodies.py (FITTED 24; SHELL_SHARE 0.99, OFFSET_MOST 0.05), clips.py, far.py; score/stages/cast (gates); CONTEXT.md "cast" (#26). -->

## Completion

A scene is complete when its gate passes on its final assembly: every row made or dropped with a reason, nothing unmade, no placeholder or resting fault, the creator's picks shown and every layer and shown scene present. A fault the creator decides to ship with is an accepted gap, written with who decided, when, why and its measured faults; the completion gate lists every gap by name and is never loosened, and a scene whose accepted gaps are its only fail is complete apart from accepted gaps. A hook stops an agent claiming a scene is done while its gate fails: agents judging their own scenes agree with a measured geometry score only 45.8 percent of the time [@li2026lego].

<!-- Accepted gaps: score/stages/gaps.py, data/checks/gaps/<place>.json; batch gaps: score/stages/batch_gaps.py. tools/usd/complete.py CHECKS; tools/usd/contents.py JUDGES; score/stages/complete; .claude/hooks/completion_guard.py. LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. -->

::: gap
**Gap: Figures 4 to 7.** (4) A scene's models painted from the library beside their close-ups; (5) a scene swept to its concept's light; (6) motion and effects in place; (7) its people and their cast. They wait on the remake's assemblies.
:::

## Prices and ledgers

Every paid stage is priced from a unit cost measured on the ledgers, times the units its forecast rule counts, times the bill's share over the ledger; a stage with no measured run has no price, and its estimate is shown apart as a guess. Machines and Google calls write ledger lines with their node's clearance, and the month's spend is the higher of ledgers and bill, which caught misses: EUR 1,554 billed against EUR 1,387 in the cloud ledger on 12 October 2026, and EUR 549 billed by Google for a day the earlier ledger put at EUR 30. A paid node runs only when every gate on its inputs passed, the month's books are known and its batch's stop has room for its forecast.

<!-- Bill against ledger: tools/props/cloud/CLAUDE.md (bill EUR 1,554 vs ledger 1,387 on 2026-10-12; Google EUR 549 vs 30 on 2026-10-11). Unit prices: data/costs/per-unit.json, tools/costs/per_unit.py; bill share: compute.bill_share (ADR-0006); guesses kept apart: score/adapters/compute run_price (guess_euros). Clearance: score/adapters/compute/__init__.py (clearance, books_refusal, require_cleared). -->

# Evidence

Environment 1 is the worked example. Its first run was not accepted by the creator and its store was lost on 19 October 2026, so this draft shows none of its outputs; its remake from new designs has not run.

<!-- The creator's review: issue #10 body. The loss: docs/bible.md architecture/failure ("Losing $PROPS_HOME", 2026-10-19, #13). -->

::: gap
**Gap: Table 1 and the film.** Per scene of the remake: inventory rows, models generated and coded, layers, gaps before and after the batch, time, euros and the creator's verdict; and a walk through environment 1. They wait on the remake's batch and the creator's review.
:::

::: gap
**Gap: Table 2, people.** Usable clips per look by the shell and clip gates on the remake's people. It waits on the people line's batch.
:::

**Agent tools.** With them an agent used about half the output and cost on two of three scenes; on the third it left more faults; one run each (Appendix E).

<!-- paper/evidence/agent-tools-bench/analysis.json; Table E1. -->

# Limitations, future work and conclusion

One creator judges, and he has not yet accepted a run. Closed models (Nano Banana Pro, Gemini 3.1 Pro) draw the concepts and close-ups and read and plan every scene; they may change or go. The design step, the finish route, the shapes-first loop and the code bodies have not yet carried a scene through a batch; the edit layer is a slot, objects are not interactive, and no game engine opens the result yet. Next: the remake's batch, an engine adapter with physics and interaction, an edit layer the assembly carries, three more environments, open models, LEGO-Bench [@li2026lego]. In short, SCORE builds an environment the way studios do, scene by scene and layer by layer, so a fault is fixed in its own layer; an accepted environment will show if it holds.

<!-- Engine: score/adapters/engines ("no game engine yet"). Closed models: score/review/concepts.py (Nano Banana Pro draws), reading.py and plan_writing.py (Gemini 3.1 Pro), score/stages/props (close-ups by Nano Banana Pro). -->

# References {-}

::: {#refs}
:::

# Appendix {-}

```{=latex}
\appendix
```

# The hub in six rounds

The surface library, one model per real-world object and the straightness check came out of six rounds of work on the hub on 6 and 7 October 2026, each answering the creator's verdict on the round before (Table A1). In the first two rounds, the creator chose between the old and the new method side by side from the same cameras.

**Table A1.** The hub's six rounds. Cost is given as rented GPU time in euros and picture-model calls in dollars. Frame time is the mean frame time on an RTX 5080, in the night scene, at 1600×900.

| Round | Change | Creator's verdict | Cost | Frame time |
|--------------|--------------------------------|--------------------------------|---------|------------|
| 1, two walls, A/B | surface library, routing by shape, room checks | chose the new method ("Y looks much cleaner") | €0.88 | 7.81 ms vs 7.53 |
| 2, two walls, A/B | 71-variant library, shared texture sets, roof check | chose the new method again | €1.70 | 8.05 ms vs 8.24 |
| 3, whole room | all stages end to end, 74 models | old models were still loaded; labels and floor fittings were wrong | €1.67 | 6.78 ms (old 9.22) |
| 4, whole room | detail through the pipeline, picture colours kept | "pretty much all of this became messy" | €8.50, $5.09 | 9.6 ms |
| 5, eight pieces, A/B | shape only from the pipeline, library surfaces, parts check | new method preferred for the door, notice board and porthole; three pieces still wrong | €0.21 | not run |
| 6, whole room | round 5 everywhere, one model per object, straightness check | "this looks amazing, I have no negative feedback" | €3.48, $1.07 | 5.6 ms |

<!-- R1: local R&D log progress-robust-exp.txt [A/B numbers], blind key, quote at "ROUND TWO". R2: [A/B round two], [spend round two]; session record 2026-10-06T16:52Z. R3: progress-robust-exp.txt round three and fix round. R4: progress-hub-r4.txt; #130 comment 2026-10-07T05:29; quote in brief job-hub-r5-test.txt. R5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt. R6: progress-hub-r5.txt ROUND SIX; #130 comments 2026-10-07T15:55 and 16:20. -->

Three findings shaped the method. First, deterministic checks catch what agents miss: in round one, the share of rays leaking out through walls and roof fell from 1.53 percent of 5,817 to zero, and the colour noise within surfaces from a median of 31.1 to 3.2 percent, but only walking through the loaded room showed 26 old models still in it, which became the made-only check. Second, generated pieces that kept their pictures' colours made the room inconsistent, so surfaces come only from the library. Third, generated composite objects melted their parts together, and generated boxes leaned (one locker by 13 degrees), which led to one model per real-world object and to the straightness check. By round six the room used 0.45 million triangles, against 1.96 million in round four, and 187 MB on disk, against 487 MB.

<!-- Numbers: progress-robust-exp.txt [A/B numbers] and round three fix round; 2099 docs/bible.md item 11 (locker); #130 comment 2026-10-07T15:55 (round six vs four). -->


# Check details

- **Room checks** cast rays to find light leaking out through walls and roof, find pieces in front of a real opening and roof and wall fittings more than 3 cm off their surface or turned more than 5 degrees from it, and count pieces, triangles and lamps against the room's budget.
- **Door check:** every door must stand in a wall or partition that fully separates its two sides, tested by walking a grid from one side to the other.
- **Model check:** every model must have walls at least 3 mm thick. A generated box fails if one of its sides tilts more than 2 degrees or is warped. Making a generated model solid stops if its bounding box grows more than 3 percent.
- **Likeness gate:** a made model's outline from eight sides must overlap its close-up's by at least 0.50, a least set on the hub's twelve accepted generated models with a margin of 0.05, and its DINOv2 [@oquab2023dinov2] similarity must reach a least set the same way; without that calibration the gate answers unknown.
- **Bake check:** each baked part within ΔE 20 (CIE76) of its surface's colour, worn and dirtied as far as its scene's wear and dirt, and within ΔE 32 of its close-up's; lightness order fails when the close-up shows one surface more than 10 L\* lighter and the bake makes it more than 3 L\* darker; one look fails when no two near-neutral surfaces bake far enough apart for a viewer to tell at the scene's view distance, while the close-up shows them more than ΔE 24 apart. What a viewer tells is measured, not set: Stone, Szafir and Setlur measured the CIELAB difference half of their viewers see between two colours s degrees wide, per axis ND(50, s) = C + K/s, with (C, K) = (5.08, 0.75) for L\*, (5.34, 1.54) for a\* and (5.35, 2.87) for b\* on sizes 1/3 to 6 degrees [@stone2014size]; two surfaces are told apart when their difference, each axis over its ND, is 1 or more. A surface's size is its model's middle size times the root of its area share, seen from the scene's nearest view. This replaced a fixed ΔE 12, which failed the wreck's access cover on a 9.3 L\* step between its steel and its scorched white that its owner sees (11.3 degrees from the nearest view; half of viewers see 5.2 L\* at that size); <!-- ND(50) constants: Stone et al. 2014, Table 3; sizes: score/stages/surfaces/bake_check.py seen_degrees on data/kit/wreck.json and data/scene/wreck.json; the cover's bake: its surfaces-check record, test in score/stages/surfaces/surfaces_test.py --> a quadrant of a standing model's base more than 3 cm off the floor fails. Glass, screens, lamps and print are judged by their own colour and left out of the order.
- **Settling and resting check:** an object that would turn more than 15 degrees or drift more than 30 cm when dropped keeps its laid pose and is marked as not resting; small debris, with no side over 1.4 m, may turn freely and drift up to 1 m. Hung objects are exempt by their inventory anchor, and fixed objects are not judged for tipping. The triage fails a foot off its support and an up axis leaning more than 3 degrees.
- **Light:** the scene's median brightness within 1.5 times its concept's and every view within 2.5 times; a lamp is blown when over 20 percent of the pixels where it gives at least half the light are white, and unlit when it gives less than 0.001 percent of every view's light.
- **Motion:** no moving thing within 3 cm of a still thing or another moving thing, read every 0.25 s; rounds join within 1 mm; speeds within each kind's cited range.
- **Sound:** CLAP score against the brief at least 0.30, the tenth percentile of 55 of the environment's picks; a take no more than 0.5 s longer than its brief.
- **People:** the shell gate passes a look when 99 percent of its soft points lie within 5 cm of the fitted body; the worst point and its joint are recorded. A clip is usable when no frame tucks more than 5 mm, no hard part stretches past 1.2 times its bind length, cloth crosses cloth no more than in the earlier body's same clip, and no part's edges pass through cloth deeper than 3 mm more often than at the bind. A far-only look is judged on its joins, likeness and the far body's triangles (at most 1,220); the near outfit's triangles and shell offset are recorded, not gating. The A-pose outline is judged against the finished Pixal3D take the build starts from; the take's own loss against the raw model is recorded apart. A crowd copy stands only where it fills under a tenth of every view's height.
- **Worse than accepted:** a measure counts as worse only when it moves the wrong way by at least its tolerance, the smallest change a viewer could see: one more fault for a count; 0.02 of full scale for lightness on 0 to 1 (a halo, fill, beam or haze wash), and 5 of 255 levels for a colour gap, the step a viewer notices between two pictures; 0.05 for a brightness ratio; one percent of the picture for a share of it; a twentieth of the Earth's lit disc; 5 mm for a length. A score no viewer reads directly, such as a likeness score, is worse by any move. Tolerances decide only whether an output waits for the creator; a check that fails still fails.
- **The creator's accept carried forward:** when the creator accepts a worse output, that accept records what was allowed, each measure's value before and after. A later output that passes every gate and is no worse than the output taken, within the tolerances, is accepted by the runner with that accept named; a move beyond it still waits for the creator.
- **What the creator acts on:** the creator rejects, accepts or waives only an output already seen on its review page. This is the creator's rule; the commands do not yet check that the page was opened.
- **Completion gate:** the requirements given in Section 3.6, each with its result tied to a fingerprint of the stage's files and inputs; a result made on another stage counts as unknown. The placeholder check judges every mesh a code builder draws, and only the shell builders pass unnamed.


**Decisions recorded in these checks.** Three people's gates are decisions of the captain, the agent session that then ran environment 1, taken on 12 and 13 October 2026 under the creator's rules and open to the creator's reversal. (1) The shell gate counts 99 percent of the soft points rather than every point, with the worst point recorded: the points beyond it were loose cloth edges (cuffs, hems, caps), which no part label names, so they could not be given a joint of their own by label. (2) A look seen only far away is judged on what is drawn far away, not on the near outfit it was made from. (3) The A-pose outline is judged against the finished take, not the raw model, so the take's own loss is not charged to the build. Earlier, the full-body cut (which looks get bodies in full and which only far ones) was set by the people's share of the budget.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). Likeness: score/stages/props/likeness.py (OUTLINE_LEAST 0.50), CLAUDE.md. Finish maps and bake: score/stages/surfaces/finish_maps.py, finish_parts.py, bake_check.py. Settling, resting and triage: tools/usd/settle.py, resting.py, triage.py (LEAN_MOST 3.0). Light: score/stages/light/mix.py (UNLIT_SHARE 0.00001). Motion: score/stages/motion (REACH_MOST 0.03, SEAM_MOST 0.001). Sound: score/stages/sound/gates.py. People: score/stages/people_bodies/bodies.py, clips.py, far.py (FAR_TRIANGLES 1220); tools/characters/maker/outline.py; score/stages/cast (FAR_SHARE 0.10). Decisions: commits 4ff0a0c (shell gate, outline), e80f07d (far-only), 9821002 and 353294e (full-body cut); issue #5, comment 6139504056. Placeholder check widened to every code-builder mesh: score 6364971. Carried accept: score/review/__init__.py (owners_allowance, within_owners_accept, allowed_moves), commit 0a6d0e4. The page rule: captain's brief of 2026-10-13; score/review/__main__.py has no check of it. Camera measure: paper/evidence/characters/people-2026-10-13.txt sections 5 and 7; score/stages/people_bodies/clips.py does not read cameras. Tolerances: score/review/__init__.py (TOLERANCES, COUNT_STEP, LIGHTNESS_STEP 0.02, LEVEL_STEP 5.0, RATIO_STEP 0.05, PICTURE_SHARE_STEP 0.01, DISC_SHARE_STEP 0.05, LENGTH_STEP 0.005). -->

# Models and licences

Every model in the framework must allow commercial use of its output (Table C1); we read each licence for its clauses on commercial use. Candidates were dropped under this rule, among them NVIDIA's Lyra 2.0 (weights for internal research only), Hunyuan3D 2.1 (licence does not apply in the European Union) and GarmentCode's fork of NVIDIA Warp (non-commercial research only), which Newton's cloth solver on upstream Warp replaced; Blender's cloth simulation [@blender] is kept as a second route. The one open doubt is the face LoRA, whose training data is not disclosed.

**Table C1.** Models in the framework.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups on the prop route, ground skins; in the first run, finish maps (the close-up drawn again with one flat colour per finish) | paid API |
| Gemini 3.1 Pro [@gemini31pro] | the environment concept's interview; scene inventories and plans; each model's finishes listed and labelled, matched to library surfaces, and rechecked | paid API |
| Qwen-Image-Edit-2511 [@qwenimageedit] | close-ups, first, in the first run's close-up stage | Apache-2.0 |
| Qwen3.8-27B [@qwen38] | the first run's close-up shape check judge; each part's material | Apache-2.0 |
| Pixal3D [@li2026pixal3d] | picture to 3D | MIT; DINOv3 licence [@simeoni2025dinov3] for its encoder |
| PartCrafter [@lin2025partcrafter] | parts | MIT; its non-commercial background remover not used |
| SegviGen [@li2026segvigen] | laid the close-up's finish map onto the 3D shape (the first run's surface stage) | MIT, on TRELLIS.2 (MIT); DINOv3 licence for its encoder; its non-commercial background remover and nvdiffrast not used |
| GeoSAM2 [@deng2025geosam2] | parts of our own model, seeded by the close-up's regions (trial) | Apache-2.0 |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surfaces | BSD-3-Clause |
| MOSS-SoundEffect v2.0, CLAP | sound | Apache-2.0 |
| World Labs [@marble_terms] | optional walkable reference | paid; outputs owned by paid users |
| FLUX.2 klein 4B [@flux2klein] | earlier prop pictures; the characters' A-pose pictures from words and their hair's clay pictures | Apache-2.0 |
| MoGe-2 [@wang2025moge2], SAM 3 [@carion2025sam3] | measuring and finding objects in pictures; boxing each inventory row on its concept; counting people and crops | MIT; SAM Licence |
| Kimodo [@rempe2026kimodo] | the characters' motion from sentences | Apache-2.0 code; NVIDIA Open Model License for the Kimodo-SOMA-RP-v1.1 weights, commercial use allowed |
| LLM2Vec [@behnamghader2024llm2vec] on Meta-Llama-3-8B-Instruct [@grattafiori2024llama3] | Kimodo's text encoder, used only while clips are made; nothing from it ships | Llama 3 Community License: commercial use allowed, the 700 million monthly users clause does not apply, "Built with Meta Llama 3" shown, no exclusion in the European Union for the text-only 8B model |
| SAM 3D Body [@yang2026sam3dbody], SAM3DBody-cpp [@sam3dbodycpp] | body shape from a picture | SAM Licence for the weights, SAM3DBody-cpp's converted ONNX and GGUF weights included whatever their tag says; MIT for SAM3DBody-cpp's code |
| SOMA-X and MHR | the characters' bodies | Apache-2.0 |
| GarmentCode [@korosteleva2023garmentcode], Newton [@newton] on Warp [@warp], Blender's cloth [@blender] | the clothes' sewing patterns and their drape | MIT; Newton and Warp Apache-2.0; Blender is GPL and its output is ours; GarmentCode's Warp fork (non-commercial research only) not used |
| Hi3DGen [@ye2025hi3dgen] | the characters' hair | MIT code; MIT and Apache-2.0 weights |
| FLUX.2 klein base 4B [@flux2kleinbase] with the refcontrol reference-depth LoRA [@refcontrol] | the characters' faces | Apache-2.0, both; the LoRA's training data is not disclosed |
| UniRig [@zhang2025unirig] | the skeleton and skin of a quadruped | MIT code and weights |
| Robust Skin Weights Transfer [@abdrashitov2023rswt] | the SOMA-X skeleton's skin weights moved onto a Pixal3D person (a trial) | MIT reference code, ported with trimesh and SciPy; libigl, whose bindings carry GPL-3.0, not used |
| MakeHuman eyes | the characters' eyes | CC0 |

The close-ups' shape check was tuned on 40 close-ups that four open picture models drew of the lab's ten objects, each scored by hand, and on Nano Banana Pro's ten pictures of the same objects. With the majority of three sampled answers, the check agreed with the hand score on 29 of the 40, passed all ten of the closed model's pictures and two marginal ones, passed none scored wrong or failed, and failed nine that were good or usable. A single answer at temperature zero was rejected: asked 51 questions twice in one batch, it changed 7 verdicts.

<!-- Tuning: progress-openpics.txt 18:53 (vote: 29/40 agree, 0 wrong/failed passed, 2 marginal passed, 9 wrong fails; Pro 10/10), greedy rejected 17:56 (7/51 differed). Lab: progress-openpics.txt 17:35 (8 Qwen, 14 Pro, 7 Pro first takes failed for the room or dimension lines, all crop-only retakes passed, EUR 4.12 cloud, $2.81 Pro). Environment 1: progress-world1-score.txt 18:55 (workshop, greenhouse, campgrounds; 17 rows) and 20:12 (10/17 accepted, all by Pro, Qwen 0/17, 7 for review, EUR 3.06, Pro $4.02). -->

The inventory readings, the plan writings, the picture-to-3D step, the finish route, the surface bakes, the sound generation, all checks and the assembly run automatically. Coding agents (Claude Code [@claudecode]) write the framework's code and every code builder, and wrote environment 1's first-run inventories and plans; in the hub's final round, 86 of its 98 models were built in code. Some steps were still done by hand: some generated objects were turned to face the right way by eye, and a few labels were placed by hand before a rule took over that job. The concept picks, the corrections drawn on concepts and plans, and the verdicts are the creator's own choices.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. Characters' licences: the characters' licence check of job characters-full, 2026-10-09 (progress-characters-full.txt 12:56, the coordinator's brief to the paper agent), recorded in tools/props/cloud/characters_setup.sh and tools/characters/maker/CLAUDE.md; Hugging Face licence tags of FLUX.2-klein-base-4B, refcontrol-FLUX.2-klein-4B-reference-depth-lora (apache-2.0) and VAST-AI/UniRig (mit), read 2026-10-09; SAM3DBody-cpp LICENSE (MIT). -->


# The surface library

The surface library holds families of variants, among them painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light, print, wood, ground, foil, water, skin and hair. After the hub's second round it held 71 variants made from 14 ProcFunc recipes; it now holds 369 variants in 26 families made from 22 recipes. Each variant is a recipe with settings, takes its colours only from the palette, and is baked into base-colour, metal-roughness and normal maps at a texture density that depends on how close a viewer can get. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor that a piece stands on. A surface the finish-map route proposes enters an append-only registry and joins the library only when the creator accepts it.

<!-- 71/14: progress-robust-exp.txt round two. 369/26/22: data/library/materials.json at 4c5365e (families' variants, recipes). Kick wear 32 cm: 2099 docs/bible.md item 11. Registry: score/stages/surfaces/registry.py. -->

# With and without the agent tools

The tools that check an agent's work were tested on three scenes of environment 1: a room (the workshop, 814 objects), an outdoor scene (the street, 1,198 objects) and a dense room (the hangar, 1,657 objects). They are the completion gate (Section 3.6); a triage of the resting check, which judges each object by what holds it up, read from its inventory row, and keeps only real faults [@tam2025sceneeval; @xia2026sage]; a pick lock, which refuses an export that would show anything but the model the creator picked for a row; and a render-and-compare, which lists the objects least like their close-ups by DINOv2 similarity [@oquab2023dinov2]. In both arms, the same agent (Claude Opus 5.5 in Claude Code, headless) started from the same exported stage and inventory and was asked to make the scene as complete as it could in about 50 minutes, through its layout data only; one arm had the framework from before these tools. Each arm ran once, so Table E1 shows what happened, not an average.

**Table E1.** One session per arm and scene. Faults are the resting triage's real faults left on the final stage, measured against the arm's own data; placeholders by the first placeholder check; rows are inventory rows with no object and no written reason. Agent cost is the session's model cost; cloud is its rented machines' cost.

| Scene, arm | Faults, start → end | Placeholders | Rows missing | Min. | Agent cost | Output tokens | Cloud | Exports | Unknown gate calls |
|--------------------|---------|---------------|--------|------|-------|-------|-------|---------|------------|
| Workshop, without | 18 → 13 | 0 → 0 | 1 → 0 | 36 | $2.26 | 30.4k | €0.85 | 7 | not used |
| Workshop, with | 18 → 0 | 0 → 0 | 1 → 0 | 26 | $1.42 | 14.3k | €0.85 | 2 | 2 of 4 |
| Street, without | 11 → 0 | 0 → 0 | 0 → 0 | 38 | $2.40 | 30.0k | €0.32 | 9 | not used |
| Street, with | 12 → 0 | 0 → 0 | 0 → 0 | 39 | $1.21 | 10.4k | €0.76 | 1 | 0 of 5 |
| Hangar, without | 14 → 4 | 5 → 0 | 0 → 0 | 47 | $2.01 | 26.6k | €0.00 | 7 | not used |
| Hangar, with | 14 → 9 | 5 → 0 | 0 → 0 | 32 | $2.34 | 29.1k | €0.64 | 5 | 3 of 6 |

The tools made building cheaper more often than they made the scene better. On the workshop and the street, the arm with the tools used about half the agent's output and cost, and exported the stage once or twice instead of seven to nine times, because the triage named the few real faults among hundreds of alarms. On the workshop, 13 of its 18 faults were cleared by writing into the inventory what holds a piece up, which the creator still has to confirm. On the hangar the arm without the tools left fewer faults: the arm with them spent its time replacing five placeholder slabs and trying the drop test, which failed on a room with no ground mesh (fixed after the run), and the nine faults it left are models with stray parts below their feet. No agent claimed a scene was complete, so the gate's hook never had to refuse a claim. No row carries an owner's pick, so the pick lock was not tested.

<!-- Benchmark: paper/evidence/agent-tools-bench: analysis.json (written by the bench's analyse.py from each session's record and transcript), and per arm and place (on = with, off = without) measure-start.json, measure-end.json, measure-manual.json and session.json. Arms: without = score 672ddfd, with = ff44157 (both with ff44157's data for the three places); claude -p --model claude-opus-5-5, 2026-10-09. The street's start reads 11 and 12 because the two start measures read the inventory from different checkouts; the stage was the same. The workshop's 13 cleared by data: 11 tool-board tools set to hanging, two arm monitors fixed (session report). -->
