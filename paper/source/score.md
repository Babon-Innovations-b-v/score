---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 8 October 2026"
abstract: |
  World models and one-shot 3D generators produce a convincing place from a sentence or a picture, but not a world a creator can build on: a stream of frames, or one fused scene without separate objects, collision or clear rights. SCORE compiles worlds instead. A creator picks references, a concept and a style; coding agents and open models compile those picks offline, through stages with explicit and checkable outputs, into one canonical scene that engines and simulators load and that keeps the creator's edits across regeneration. Four mechanisms make the output coherent and cheap to get right: deterministic checks before every paid step, a parts check that decides between code and generation with one model per real-world object, a shared rule-based surface library that keeps shape and surface apart, and review tools that put every stage's output in front of the creator, who decides at a few fixed points. We apply the same route to four worlds of different kinds.
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main body: the core contribution only. Specifics (thresholds, budgets, settings, history)
    are in the appendix.
  - Every number is read from a file named in a comment beside it. "Local R&D log" means the
    build sessions' own logs, to be published with the framework.
  - The world step (World Labs Marble in our runs) is one optional step; no result compares it
    with another model or judges it on its own.
-->

::: gap
**Gap: Figure 1, teaser.** Four worlds made with SCORE (the game world of 2099, a stylised underwater world, a simulation world for robots, a third-person fantasy world), each as its picked concept beside the finished world in its engine. Waits on the four worlds being finished and accepted by their creators.
:::

# Introduction

A creator who wants a world for a game, a film or a robot to train in needs it complete and owned. Complete means every door, floor, object, light and sound exists and works wherever the player looks. Owned means the creator decides what the world is, can change any part later without starting over, and holds the rights to all of it.

World models make the first impression of a world cheap, but give neither. Genie 3 renders a world a person can move through in real time, with a constrained range of actions and minutes of interaction among its stated limits [@genie3; @bruce2024genie]. One-shot 3D world generators return "static monolithic assets with limited editability and physical interaction" [@hu2026worldact].

SCORE builds the whole world, offline, and ships it as files. The creator writes the score, and coding agents and open tools play it: the creator decides at a few fixed points, and between them every stage hands on explicit data or code that an agent can read and a deterministic check can test before money is spent. Our contributions:

- **SCORE as a world compiler:** staged, cached compilation from a creator's picks into one canonical scene with generated base layers and the creator's edit layers (Section 3).
- **Four mechanisms** that keep compiled worlds coherent and cheap to get right (Section 4).
- **Evidence across four worlds of different kinds**, with time, cost and faults caught before spending at every stage, and an evaluation on a shared benchmark (Sections 5 and 6).

# Related work

**World models and world generators.** Genie learns an interactive environment from video [@bruce2024genie]; WorldGen generates traversable worlds from text [@wang2025worldgen]; WorldAct and WorldSculpt recover separate objects from generated worlds or video [@hu2026worldact; @niu2026worldsculpt]. They generate the world itself; SCORE uses a world generator at most as an optional reference step and ships only compiled scenes.

**Agents that build scenes.** Holodeck solves language-model layout constraints over retrieved objects [@yang2024holodeck]; SceneCraft and recursive code world models write scenes as programs [@hu2024scenecraft; @li2026rcwm]; WorldClaw and AutoUE assemble open worlds and game code with agents [@guo2026worldclaw; @yin2026autoue]. LEGO-Anything finds that coding agents start scenes weakly, regress while editing and judge geometry unreliably, and answers with tools rather than training [@li2026lego]. SCORE applies that stance to worlds that do not exist yet, built to a person's picks rather than rebuilt from a photograph.

**Procedural generation, parts and style.** Infinigen and Infinigen Indoors generate worlds and rooms from rules, with materials as their own generators [@raistrick2023infinigen; @raistrick2024indoors]; ProcFunc gives them an interface language models write well [@raistrick2026procfunc]. PartCrafter and Point2Part split shapes into parts [@lin2025partcrafter; @tsui2026point2part]. Style across generated assets remains open [@wu2026production; @yang2026flowscene]; Hunyuan3D Studio fixes it at the picture [@lei2025hunyuanstudio]. SCORE takes surface out of the generated models entirely.

# SCORE as a world compiler

A compiler turns a source a person wrote into an output a machine runs, through stages whose intermediate forms can be inspected, cached and checked. In SCORE the source is the creator's picks: references, a concept picture and a style for each place. The output is a world an engine loads. Compilation happens once, offline, in cloud batches; nothing is generated while the world is played, and each scale of a world (a room, a planet's ground, an orbit) is its own kind of world rather than one continuous zoom.

The stages are concept, dimensioned plan, inventory, close-ups, shape, surfaces, sound, assembly and review. Each writes an explicit output: a plan in metres, an inventory row for every object with its parent, one clean picture per object, one model per object, baked surfaces, sounds. Each output is cached, so changing one pick recompiles only the stages downstream of it.

All stages write one canonical scene: an OpenUSD stage [@openusd] with glTF geometry [@gltf2]. Every object carries its kind, place in metres, collision, the library surface of each part, its sound, and tags for what a person can do with it, such as door, seat, terminal or airlock. The compiler owns a generated base layer and may rewrite it; the creator's changes live in edit layers above it, so recompiling replaces the base and keeps every edit. Engines and simulators load the same stage through thin adapters.

::: gap
**Gap: Figure 2, the compiler.** The stages with their cached outputs, the scene's base and edit layers, and the engine adapters. To be drawn with the scene export, which is being built in the framework repository.
:::

# Key mechanisms

## Checks before spending

A fault costs nothing in the plan, cents at a picture, tens of cents and an hour at a 3D model, and an evening of the creator's time once a place is built and played. Every paid stage is therefore gated by deterministic checks on real geometry, never by an agent's judgement, and a failure sends work back one stage, never forward with a flag. The checks cover the room (leaks, blocked openings, pieces off their surface, doors that do not separate their sides), the inventory against the concept, each model (closed, thick enough, straight), the surfaces against the palette and budget, and the assembled scene, including any visible mesh the route did not make (Appendix D).

<!-- Fault cost per stage (€0.18 and 75 minutes at the model): 2099 paper writing/outline.md 9f. -->

## Code or pipeline: the parts check

Picture-to-3D models build chunky solids well and flat panels, thin beams and openings badly; agent-written code builders are exact, light and straight but show only the parts the agent wrote. SCORE decides per object kind with the **parts check**: a kind is built in code only when its code build shows every part its clean close-up shows; otherwise it is generated from the close-up with Pixal3D [@li2026pixal3d] and made solid. Composites are split before anything is made, one model per real-world object, so a console is a desk carrying its monitors and keyboards rather than one fused mesh.

## Shape and surface apart

Models and code give shape only. Every part takes one surface from a shared library of ProcFunc functions [@raistrick2026procfunc] built on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette, with wear, dirt and seed as named settings. A room has one wear setting, applied from causes such as edges and foot traffic, so every piece in it agrees on what worn steel looks like. Parts of a generated model come from PartCrafter [@lin2025partcrafter]; each part takes one library surface, and the picture only chooses which. Sound is compiled the same way: surfaces carry their footsteps and impacts, rooms their echo, objects their own sound, generated in one batch by MOSS-SoundEffect [@moss2026] and chosen against its prompt by CLAP [@wu2022clap] (Appendix F). The surface and sound libraries grow with each world and are reused in the next.

## Review tools for the creator

The creator picks references, concept and style, and reviews each place; nothing else waits on a person. SCORE supplies the review tools: pages that show each stage's outputs side by side, before and after shots from the same cameras, in-engine walkthroughs, and the results of every check. How the creator forms a judgement with them is the creator's own. The creator's reviews are what steered the mechanisms above (Appendix C).

::: gap
**Gap: Figure 3, one place through the stages.** One place from concept to finished world, with the output of each stage and the checks that fired on it. Waits on a place built and accepted on the final route.
:::

# Results across worlds

We build four worlds with the same route: the game world of 2099 (a Moon base, its surroundings, a Mars camp and a prologue on Earth), a stylised underwater world, a simulation world for robots and a third-person fantasy world.

::: gap
**Gap: Table 1, results per world and stage.** For each world: places, wall time, cost in GPU time and picture calls, models built in code and generated, and faults caught before spending at each stage against faults found after. Waits on world 1 being finished and reviewed by its creator (most places are built, none after its first room yet reviewed in play) and on worlds 2 to 4. Per-place records are in Appendix B.
:::

::: gap
**Gap: Figure 4, one place per world.** A representative place from each world beside its concept, from the concept's own camera. Waits on the same worlds; all places are in Appendix A.
:::

# Evaluation

::: gap
**Gap: LEGO-Bench.** Scores on LEGO-Bench [@li2026lego], the benchmark of scenes rebuilt from pictures. Waits on the benchmark's code release and on SCORE's scene export with its Blender adapter.
:::

::: gap
**Gap: ablations.** The route with and without the optional world step (a walkable whole-room reference made from the concept), and with checks before spending switched off, on the same places: concept coverage, density of the built room, cost, faults after spending, and the creator's review. Waits on the route running from the framework repository.
:::

::: gap
**Gap: style coherence.** A measure of whether a place keeps one style, from rendered frames (colour distance to the palette per kind of source, lightness spread, ink density), validated against the creator's reviews. Designed, not built.
:::

# Limitations and outlook

Code builders are clean but need an agent to write one per kind of object, which does not scale as well as generation. A concept shows one side of a place, so built places come out sparser than their concepts; the concept-density check catches this but does not fix it, and the optional world step is meant to. Daily quotas on picture models, not compute cost, set the pace of a build. Next, the simulation world needs masses, friction and joints compiled into the scene for robots, and scales that are computed rather than modelled enter as open solvers wrapped as stages, starting with REBOUND for orbits [@rein2012rebound].

<!-- Code builders and sparse rooms: issue JoeyKardolus/2099#130 (lab, greenhouse, 2026-10-07/08); session record 2026-10-08T09:27Z. Quotas: #130 comment 2026-10-08T09:18. -->

# References {-}

::: {#refs}
:::

# Appendix {-}

```{=latex}
\appendix
```

# Per-world demos

::: gap
**Gap.** Every place of every world as its concept beside the finished build, plus links to demo videos and playable builds. Waits on the worlds.
:::

# Detailed per-stage results

::: gap
**Gap.** For every place: wall time, cost, models in code and generated, and each fault caught before or found after spending, by stage and check. World 1's per-place records exist for 21 place runs but are not results until the world is finished and reviewed; worlds 2 to 4 are not started.
:::

<!-- 21 place runs: scaling-world1.tsv (local R&D log). -->

# Development history: the hub

The mechanisms of Section 4 came out of six rounds on one room, the central hub of the game 2099, on 6 and 7 October 2026, each answering the creator's verdict on the last (Table C1). The first two rounds were decided by side-by-side comparison of the old and new route on the same cameras.

**Table C1.** The hub's six rounds. Cost: rented GPU time (€) and picture calls ($). Frame time: mean on an RTX 5080 at night, 1600×900.

| Round | Change | Creator's verdict | Cost | Frame time |
|---|---|---|---|---|
| 1, two walls, A/B | surface library, routing by shape, room checks | preferred the new route ("Y looks much cleaner") | €0.88 | 7.81 ms vs 7.53 |
| 2, two walls, A/B | 71-variant library, shared texture sets, roof check | preferred the new route again | €1.70 | 8.05 ms vs 8.24 |
| 3, whole room | route end to end, 74 models | old models still loaded; labels and floor fittings wrong | €1.67 | 6.78 ms (old 9.22) |
| 4, whole room | detail through the pipeline, picture colours kept | "pretty much all of this became messy" | €8.50, $5.09 | 9.6 ms |
| 5, eight pieces, A/B | shape only from the pipeline, library surfaces, parts check | new method preferred for door, notice board, porthole; three pieces still wrong | €0.21 | not run |
| 6, whole room | round 5 everywhere, one model per object, straightness check | "this looks amazing, I have no negative feedback" | €3.48, $1.07 | 5.6 ms |

<!-- R1: local R&D log progress-robust-exp.txt [A/B numbers], blind key, quote at "ROUND TWO". R2: [A/B round two], [spend round two]; session record 2026-10-06T16:52Z. R3: progress-robust-exp.txt round three and fix round. R4: progress-hub-r4.txt; #130 comment 2026-10-07T05:29; quote in brief job-hub-r5-test.txt. R5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt. R6: progress-hub-r5.txt ROUND SIX; #130 comments 2026-10-07T15:55 and 16:20. -->

Three findings shaped the method. Deterministic checks catch what agents miss: in round one, light leaking through walls and roof fell from 1.53 percent of 5,817 rays to zero and colour noise within surfaces from a median of 31.1 to 3.2 percent; but only walking the loaded room showed 26 old models still in it, which became the made-only check. Keeping each picture's colours made every piece bring its own wear, so surfaces now come only from the library. Generated composites melted their parts together and generated boxes leaned (a locker by 13 degrees), which led to one model per object and the straightness check (shown below). Round six drew 0.45 million triangles against round four's 1.96 million and took 187 MB on disk against 487.

<!-- Numbers: progress-robust-exp.txt [A/B numbers] and round three fix round; 2099 docs/bible.md item 11 (locker); #130 comment 2026-10-07T15:55 (round six vs four). -->

![The hub's tool board in round four (left: one generated model with its picture's colours over library surfaces) and round six (right: a code-built board carrying 26 separately made tools, library surfaces only). Same camera and build.](figures/hub-toolboard-r4-r6.jpg){width=100%}

# Check details

- **Room checks**, about two seconds a room on the laid-out meshes: rays leaving through walls and roof (leak), pieces in front of a real opening, roof and wall gear more than 3 cm off its surface or turned more than 5 degrees from it, and the piece, triangle and lamp budget.
- **Door check:** every door stands in a wall or partition that fully separates its two sides, read as a walk on a grid.
- **Concept-density check:** the concept is cut into crops; every visible element has an inventory row or a written reason; after the build the place is shot from the concept's camera beside the concept.
- **Parts check:** each close-up part at least 10 percent visible from in front in the code build, and no label over a part.
- **Model check:** closed solids with walls of at least 3 mm; a generated box fails when a side tilts more than 2 degrees or warps; a solid step that grows its box more than 3 percent past the model stops itself.
- **Palette sweep and storage budget:** every model's colours against the place's library palette; 250 MB on disk and 640 MB of textures on the GPU per room.
- **Scene and made-only checks** in the engine: what floats, sinks or overlaps, and any visible mesh the route did not make, which can never be waived.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). -->

# Models and licences

Every model must allow commercial use of its output (Table E1). Licences were read for their commercial-use clauses.

**Table E1.** Models in the route.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups, ground skins | paid API |
| Pixal3D [@li2026pixal3d] | picture to 3D | MIT; DINOv3 licence [@simeoni2025dinov3] for its encoder |
| PartCrafter [@lin2025partcrafter] | parts | MIT; its non-commercial background remover not used |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surfaces | BSD-3-Clause |
| MOSS-SoundEffect v2.0, CLAP | sound | Apache-2.0 |
| World Labs Marble [@marble_terms] | optional world step | paid; outputs owned by paid users |

Picture-to-3D, parts, surface bakes, sound, checks and assembly are automatic. Coding agents (Claude Code [@claudecode]) write the plans, inventories and every code builder; in the hub's final round 86 of its 98 models were code. Hand steps remained: some generated objects turned to face the right way by eye, a few labels placed by hand before a rule replaced that. Concepts and verdicts are the creator's picks.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. -->

# Surface library and sound

The library holds families of variants (painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light and print; 71 variants from 14 ProcFunc recipes after the hub's second round), each a recipe with settings, coloured only from palette tokens and baked to base colour, metal-roughness and normal maps at a texel density by reach. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor a piece stands on. Every sound has a brief written from its object; four takes are generated, scored by CLAP against the prompt less measured faults (clipping, unsteady loops, bad joins), and levelled to one loudness per kind under a -3 dBTP true peak. A creator may swap any take; for the game 2099 all 61 sounds were generated as 244 takes in one batch for €1.61, and the creator kept recordings for three kinds (breathing, a sliding door, steps on steel).

<!-- 71/14: progress-robust-exp.txt round two. Kick wear 32 cm: 2099 docs/bible.md item 11. Sound: 2099 docs/bible.md item 12; 2099 paper writing/status.md, seventh pass. -->

# Cost and infrastructure

Every heavy step runs on rented machines deleted after each batch: NVIDIA L4 cards for picture-to-3D, parts and bakes, processor machines when cards are out of stock. The engine's tests, shots and frame-time bench also run on rented machines; a full test run took 542 s there against 596 s locally, and L4 frame times convert to the local RTX 5080 by a measured factor of 3.47. Pictures cost about $0.134 each at the resolution used. The binding limit in practice was the picture model's shared daily quota of 250 pictures, not compute.

<!-- 542 vs 596 s, 3.47: #130 comments 2026-10-07T21:57 and 23:02. $0.134: 2099 paper README "What it cost". 250 a day: #130 comment 2026-10-08T03:31. -->

::: gap
**Gap: cost tables.** Cost per batch kind and per world, reconciled with the cloud bill. Waits on the worlds; the per-place figures so far are floors from the build logs.
:::
