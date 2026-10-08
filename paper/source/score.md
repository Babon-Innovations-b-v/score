---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 8 October 2026"
abstract: |
  World models and one-shot 3D generators can produce a convincing place from a sentence or a picture, but their output is hard to build on: a stream of frames, or one fused scene without separate objects, collision or clear rights. We present SCORE, a framework that treats world creation as offline compilation. A creator picks references, a concept and a style; coding agents and open models then compile those picks, in cloud batches, through stages with explicit and checkable outputs: a dimensioned plan, an inventory of objects, one model per real-world object, surfaces from a shared rule-based library, generated sound, and a scene a game engine loads. Cheap deterministic checks run before every paid step, and every model in the route allows commercial use of its output. We report a first case study, the game world of the game 2099. Its central room was rebuilt in six rounds; the creator preferred the new route in both blind comparisons and accepted the sixth round. The rest of the world was then built on the same route, at a recorded cost of €46.67 of rented GPU time and $40.72 of picture-model calls, and showed clear weaknesses: most models were written as code by agents, and rooms came out sparser than their concepts. This is a system description with a single case study and no comparison yet; benchmark evaluation is planned.
---

<!--
  Draft conventions.
  - Every number is read from a file, named in a comment like this one. "Local R&D log" means
    the build sessions' own logs on the author's machine, to be published with the framework.
  - Work not done is said in the text as planned or in progress, never shown as a result.
  - The world step (World Labs Marble in our runs) is one optional step of the method. No result
    here compares it with another model or judges it on its own.
-->

# Introduction

Anyone making a world for a game, a film or a robot to train in needs it to be complete and to be theirs. Complete means doors open, floors hold, every object can be found, moved and given behaviour, and rooms have light and sound. Theirs means the creator decides what the world is, can change any part later without starting over, and holds the rights to all of it.

Generative models have made the first impression of a world cheap, but not this. Genie 3 renders a world a person can move through in real time, with a constrained range of actions and a few minutes of continuous interaction among its stated limits [@genie3; @bruce2024genie]. One-shot 3D world generators return one fused asset; a recent paper describes such outputs as "static monolithic assets with limited editability and physical interaction" [@hu2026worldact].

SCORE takes the opposite approach: build everything in full, offline, so the world cannot break when a player looks somewhere unexpected and can be used today in existing engines. The creator writes the score; coding agents and open tools play it. The creator decides at a few fixed points (references, concept, style, review); between those points, every stage hands on explicit data or code that an agent can read and a deterministic check can test before money is spent. Neither this approach nor a world model's is right in general; they serve different needs.

This paper describes the framework as a world compiler (Section 3) and reports one case study, the game world of 2099, built by one creator directing Claude Code agents (Section 5). We separate what was automatic, what an agent wrote, what was fixed by hand and what was a human pick, and we leave each unfinished part visible where it belongs, with the reason it is not done yet. SCORE is unrelated to WorldScore, a world-generation benchmark [@duan2025worldscore], to score distillation [@poole2022dreamfusion] and to SCoRe [@kumar2024score].

# Related work

**World models and world generators.** Genie learns an interactive environment from video [@bruce2024genie]. WorldGen generates traversable, editable worlds from text [@wang2025worldgen]; WorldAct decomposes a monolithic generated world into objects after the fact [@hu2026worldact]; WorldSculpt composes per-object meshes from grounded video [@niu2026worldsculpt]. SCORE ships no world-model output; a world generator may appear only as an optional reference step (Section 3.6).

**Agents that build scenes.** Holodeck has a language model write spatial constraints for a solver [@yang2024holodeck]; SceneCraft and recursive code world models write scenes as programs and compare renders with a reference [@hu2024scenecraft; @li2026rcwm]; WorldClaw and AutoUE use agents to assemble open worlds and game code [@guo2026worldclaw; @yin2026autoue]; 3D-RE-GEN and SceneConductor decompose one picture into placed objects [@sautter2025regen; @kim2026sceneconductor]. LEGO-Anything is closest in spirit: its coding agents show "weak scene initialization, regressive edits during iteration, and unreliable self-evaluation", addressed with tools rather than training [@li2026lego]. SCORE shares that position but builds worlds that do not exist yet, to a person's picks.

**Procedural generation, parts and style.** Infinigen and Infinigen Indoors generate worlds and rooms from rules, with materials as their own generators [@raistrick2023infinigen; @raistrick2024indoors]; ProcFunc gives these generators an interface on which language models make far fewer coding errors [@raistrick2026procfunc]. PartCrafter and Point2Part split shapes into parts [@lin2025partcrafter; @tsui2026point2part]. Keeping one style across generated assets is named as open [@wu2026production; @yang2026flowscene]; Hunyuan3D Studio fixes it at the picture [@lei2025hunyuanstudio]. SCORE instead takes surface out of the generated models altogether.

# Method

## Stages

SCORE compiles a world once, offline, in batches; nothing is generated while it is played. Each stage's output is explicit and inspectable:

1. **Concept.** A picture model draws concepts from the creator's references; the creator picks one.
2. **Dimensioned plan.** A coding agent turns the concept into a plan in metres: shell, doorways, walkways, floor levels.
3. **Inventory.** Every object becomes a row with kind, anchor, size and count; composites become a parent row with children (Section 3.3).
4. **Close-ups.** One clean, front-on picture per object.
5. **Shape.** Each kind is either built by a code builder that an agent writes, or made by the prop pipeline: Pixal3D [@li2026pixal3d] in a cloud batch, closed into a solid, triangles set by size.
6. **Surfaces.** Every part takes one surface from the shared library (Section 3.4), baked in the cloud.
7. **Sound.** Generated per surface, room and object (Section 3.4).
8. **Assembly and review.** The scene is assembled for the engine, shot from fixed cameras and reviewed by the creator, who keeps it or sends it back one stage.

A compiler needs one intermediate form all stages agree on. In the case study that form is glTF 2.0 models [@gltf2] plus one JSON layout per place, read by a Godot adapter [@godot]. The intended canonical form is an OpenUSD stage [@openusd] with a generated base layer the compiler may rewrite and edit layers that hold the creator's changes, so edits survive regeneration, loaded by thin adapters for other engines and simulators. That scene format is not used yet: the case study ran inside one game on one engine, and the export with its layer split and a second adapter (Blender first) is being built in the framework repository.

## Checks before spending

A fault costs nothing in the plan, cents at the picture, about €0.18 and 75 minutes at the 3D model, and an evening of the creator's time once a room is built and played. Each paid stage is therefore preceded by cheap deterministic checks on real geometry, and a failure sends work back one stage. Room checks cast rays for light leaks, pieces blocking openings and pieces off their surface (about two seconds a room); a door check requires every door to fully separate its two sides; a concept-density check requires every element of the concept to have an inventory row or a written reason; a model check requires closed solids with walls of at least 3 mm and fails generated boxes that tilt more than 2 degrees; a palette sweep and a storage budget (250 MB on disk, 640 MB on the GPU per room) follow; after install, a scene check finds what floats or sinks and fails on any visible mesh the route did not make.

<!-- Fault cost per stage: 2099 paper writing/outline.md 9f. Checks and limits: 2099 docs/bible.md items 11-12; local R&D logs progress-robust-exp.txt, progress-hub-r5.txt; issue JoeyKardolus/2099#130, 2026-10-07. -->

## Code or pipeline, one model per object

Picture-to-3D models handle chunky solids well and flat panels, thin beams and openings badly; in the case study they made panels about as deep as they were wide and beams 3 to 10 times too thick. Agent-written code builders are exact and light but show only the parts the agent thought to write. The routing rule that held is a check, the **parts check**: a kind is built in code only when its code build shows every part its clean close-up shows (each at least 10 percent visible, no label over a part); otherwise it goes through the prop pipeline. Composites are split before generation, one model per real-world object: a tool board is a code-built board carrying 26 separately made tools, a console its monitors and keyboards.

<!-- Panels and beams: 2099 paper writing/outline.md 9e. Parts check and composites: 2099 docs/bible.md item 11, rounds five and six. -->

## Surfaces and sound

Models and code give shape only. Every part takes one surface from a shared library of ProcFunc functions [@raistrick2026procfunc] built on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette tokens, with wear, dirt and seed as named settings; a room has one wear setting, applied from causes such as edges and foot traffic. On a generated model, PartCrafter parts [@lin2025partcrafter] laid onto the shape decide which surface each part takes. Labels go on as a few decals. The library held 71 variants in 12 families from 14 recipes after its second round. Which surface a whole part takes is still chosen by votes of its faces' picture colours, and shading in the picture can flip faces between surfaces; assigning one surface per part, with the picture only choosing which, is being built and was not in place for the case study. Sound is compiled the same way: each surface carries its footsteps and impacts, each room its echo, each inventory row its own sound, all generated in one batch by MOSS-SoundEffect v2.0 [@moss2026], chosen by CLAP prompt match [@wu2022clap] less measured faults, and levelled under a -3 dBTP true peak.

<!-- 71/12/14: local R&D log progress-robust-exp.txt, round two. Sound: 2099 docs/bible.md item 12. -->

## Cloud batches and human picks

Every heavy step runs in a rented cloud batch that is deleted afterwards, records its cost, and stops itself if its output grows past its expected size. The creator's picks happen at fixed points; where two routes compete the pick is blind, both drawn the same way and labelled X and Y at random.

## The optional world step

A concept shows one view. An optional world step can turn it into a walkable whole-room reference from which every object and every wall can be seen (World Labs Marble in our runs). Its output is never shipped. The case study below was built without it. Whether it makes fuller rooms is not yet known: the comparison of the route with and without the step, as an ablation of the method, has not been run, because the game work was paused the day the first internal run began.

<!-- Route ran without the world step from 2026-10-07: session record of 2026-10-08; local R&D log progress-worldstep.txt. -->

# Implementation

The route runs as Python tools (planning, routing, baking, install, checks), engine-side checks in Godot, and runners for rented NVIDIA L4 machines with headless Blender 5.0.1 [@blender]. It currently lives inside the game's repository; moving it into the framework repository, engine-agnostic, is the next step, so the route cannot yet be run from this repository on its own. The work was done by Claude Code agent sessions [@claudecode] directed by one person; up to twelve ran at once during the world build. Table 1 lists the models used; licences were read for their commercial-use clauses only, and this is not legal advice.

**Table 1.** Models and services in the route.

| Model or service | Used for | Licence or terms |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups, ground skins | paid API |
| Pixal3D [@li2026pixal3d] | picture-to-3D shape | MIT; DINOv3 encoder [@simeoni2025dinov3] under its own licence |
| PartCrafter [@lin2025partcrafter] | part boundaries | MIT |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surface library | BSD-3-Clause |
| MOSS-SoundEffect v2.0 [@moss2026], CLAP [@wu2022clap] | sound | Apache-2.0 |
| World Labs Marble [@marble_terms] | optional world step only | paid; outputs owned by paid users |

**What was automatic and what was not.** Picture-to-3D, part splitting, surface bakes, sound, all checks and install were automatic. Every code builder was written by a coding agent from a close-up; in the central room's final round 86 of its 98 models were code. Some generated objects were turned to face the right way by eye, a few labels were placed by hand before a rule replaced that, and agents fixed the faults the checks found. Concepts and verdicts were the creator's picks, except where an agent's interim concept pick is marked as such.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Twelve agents: session record 2026-10-08T00:28Z. -->

# Case study: the world of 2099

2099 is a first-person automation game on a Moon base, with a prologue on Earth and a Mars expedition camp. Its central room, the hub, served as the test bench for the route; the rest of the world was then built on the route the hub settled.

## The hub in six rounds

The hub's structure came from a cutaway the creator picked from twenty drawn from his reference pictures (Figure 1). It was then rebuilt six times on 6 and 7 October 2026 (Table 2).

![The picked concept for the hub (cutaway C12): a twelve-sided shell over a sunken pit, drawn by Nano Banana Pro from reference pictures the creator kept. It fixes the room's structure and is not shipped.](figures/hub-concept-c12.jpg){width=80%}

**Table 2.** The hub's six rounds. Cost is rented GPU time (€) and picture calls ($). Frame time is the mean on an RTX 5080 at night, 1600×900.

| Round | Change | Creator's verdict | Cost | Frame time |
|---|---|---|---|---|
| 1, two walls, A/B | surface library, routing by shape, room checks | blind pick for the new route ("Y looks much cleaner") | €0.88 | 7.81 ms vs 7.53 |
| 2, two walls, A/B | 71-variant library, shared texture sets, roof check | blind pick for the new route | €1.70 | 8.05 ms vs 8.24 |
| 3, whole room | route end to end, 74 models | old models still loaded; labels and floor fittings wrong | €1.67 | 6.78 ms (old 9.22) |
| 4, whole room | detail through the pipeline, picture colours kept | "pretty much all of this became messy" | €8.50, $5.09 | 9.6 ms |
| 5, eight pieces, A/B | shape only from the pipeline, library surfaces, parts check | new method preferred for door, notice board, porthole; three pieces still wrong | €0.21 | not run |
| 6, whole room | round 5 everywhere, one model per object, straightness check | "this looks amazing, I have no negative feedback" | €3.48, $1.07 | 5.6 ms |

<!-- R1: progress-robust-exp.txt [A/B numbers], blind key, quote at "ROUND TWO". R2: [A/B round two], [spend round two]; session record 2026-10-06T16:52Z. R3: progress-robust-exp.txt round three and fix round. R4: progress-hub-r4.txt; #130 comment 2026-10-07T05:29; quote in brief job-hub-r5-test.txt. R5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt. R6: progress-hub-r5.txt ROUND SIX; #130 comments 2026-10-07T15:55 and 16:20. -->

Three findings came out of it. First, deterministic checks found what agents missed: in round one, light escaping through walls and roof fell from 1.53 percent of 5,817 rays to zero, and colour noise within surfaces from a median of 31.1 to 3.2 percent. They did not find what only play showed: in round three 26 old models were still loaded, which led to the check that fails on any visible mesh the route did not make. Second, the split between code and pipeline was the hard decision: routing by shape lost detail (round three), keeping each picture's colours made every piece bring its own wear (round four), and the parts check with library-only surfaces and one model per object was what the creator accepted (Figure 2). Third, consistency and cost moved together: round six drew 0.45 million triangles against round four's 1.96 million, at 5.6 against 9.6 ms a frame and 187 against 487 MB on disk.

<!-- 1.53% of 5,817; 31.1 to 3.2%: progress-robust-exp.txt [A/B numbers]. 26: round three fix round. Round six vs four: #130 comment 2026-10-07T15:55. -->

![The hub's tool board in round four (left: one generated model with its picture's colours over library surfaces) and round six (right: a code-built board with 26 separately made tools, library surfaces only). Same camera and build.](figures/hub-toolboard-r4-r6.jpg){width=100%}

## The rest of the world

After the hub was accepted, the route was run on the other places in parallel, about one agent per place, from the evening of 7 October until the game work was paused at noon on 8 October. The per-place records (21 entries) cover the planned Moon ground, the old station and the wreck, the base's lab, workshop, greenhouse, habitat, airlock and walkway tubes, the prologue's flat, stairwell, street, square and launch view, and the Mars ground, camp grounds and habitat. Together they record €46.67 of rented GPU time and $40.72 of picture calls, as floors from the agents' notes, and 971 models: 865 code builders and 106 through the prop pipeline. Single places mostly cost a few euros, while their wall time ran to many hours, much of it waiting for machines and quotas.

<!-- All figures: scaling-world1.tsv (local R&D log), 21 rows summed; the garage row's "~2.60" counted as 2.60; shared rows counted once. -->

The creator accepted the old station and the wreck on first sight ("it just looks great"), and preferred the planned Moon ground to a crater generated with Infinigen, in a comparison that was not blind because the two were rendered differently. The other places are built and pass their checks, but have not been reviewed by the creator in play: the game work was paused before that review, so their acceptance is open. The weaknesses were consistent across places. Code builders gave clean pieces but sparse rooms, and do not scale: each kind needs an agent to write a builder. Rooms read sparser than their concepts, which a concept shows from one side only; this gave rise to the concept-density check. Choosing surfaces by picture colour produced patchy materials. And the pace was set by daily picture quotas and GPU stock, not by compute cost. A count of faults caught per check, before and after spending, belongs here and is not given: the per-place records hold the faults as free text, which still has to be coded by hand.

<!-- Old station and wreck: #130 comment 2026-10-07T21:16. Ground: progress-moonground.txt 23:44. Patchy surfaces, quotas: session record 2026-10-08T09:27Z; #130 comments 2026-10-08T03:31, 09:18. -->

# Evaluation

**Benchmark.** SCORE has not been compared with any other system. The intended evaluation is LEGO-Bench [@li2026lego], which scores scenes rebuilt from pictures in Blender. It has not been run: its code is not released yet, and SCORE first needs the scene export and Blender adapter described in Section 3.1, which are being built.

<!-- LEGO-Bench scorer in Blender: 2099 docs/bible.md, Blender coding agents (#128, "the version LEGO-Anything's scorer runs"). Code not released: 2099 paper material/07-sources.md [29]. Proposed coherence test: 2099 paper README, "Coherence: the first failure, and a proposed measure". -->

**Style coherence.** Whether a room keeps one style is judged here only by the creator's eye on pages and in play. A measured test (colour distance to the palette per input class, lightness spread, ink density) has been proposed for the game but not built, so no coherence number is reported.

**Breadth.** One world of one kind is not evidence that the framework generalises. Three more worlds are planned to test that: a stylised underwater world, a physically accurate simulation world for robots, which needs masses, friction and joints the route does not yet produce, and a third-person fantasy world. Scales that are computed rather than modelled, such as orbits, would enter as open solvers wrapped as stages, starting with REBOUND [@rein2012rebound]; none is wrapped yet.

# Limitations

This is a single case study by one creator, and every verdict in it is his; two were blind, the rest were not. Most models were written as code by a coding agent, which says as much about the agent as about the framework. Costs are floors from the agents' notes, not reconciled with the cloud bill, and the creator's and agents' time is not costed. Licences were read for their commercial clauses only.

# Availability

SCORE and this paper are developed in the open at <https://github.com/Babon-Innovations-b-v/score> under the MIT licence. The build logs cited in this draft will be published with the framework code.

# References {-}
