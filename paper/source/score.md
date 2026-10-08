---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 8 October 2026"
abstract: |
  World models and one-shot 3D generators produce a convincing place from a sentence or a picture, but not a world a creator can build on: their output is a stream of frames or one fused scene, without separate objects, collision or clear rights. SCORE treats world creation as offline compilation. The creator picks references, a concept and a style; coding agents and open models compile those picks in cloud batches, through stages with explicit and checkable outputs, into a canonical OpenUSD scene that engines and simulators load. Every object is its own model, every surface comes from one shared rule-based library, sound is generated per surface, room and object, cheap deterministic checks run before every paid step, and every model in the route allows commercial use of its output. The creator's edits live in their own layers and survive regeneration.
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - The draft has the final paper's structure. Settled content is written fully; every place
    where final content will go holds a gap box saying what goes there and what it waits on.
  - Every number is read from a file, named in a comment beside it. "Local R&D log" means the
    build sessions' own logs, to be published with the framework.
  - The world step (World Labs Marble in our runs) is one optional step. No result compares it
    with another model or judges it on its own.
-->

::: gap
**Gap: teaser figure.** One row per world built with SCORE (the game world of 2099, a stylised underwater world, a simulation world for robots, a third-person fantasy world), each showing the creator's picked concept beside the finished world in its engine. Waits on the four worlds being finished and accepted by their creator.
:::

# Introduction

A creator who wants a world for a game, a film or a robot to train in needs it complete and owned. Complete means every door, floor, object, light and sound exists and works when the player looks anywhere. Owned means the creator decides what the world is, can change any part later without starting over, and holds the rights to all of it.

World models make the first impression of a world cheap but give neither. Genie 3 renders a world a person can move through in real time, with a constrained range of actions and a few minutes of continuous interaction among its stated limits [@genie3; @bruce2024genie]. One-shot 3D world generators return "static monolithic assets with limited editability and physical interaction" [@hu2026worldact].

SCORE takes the opposite approach. It builds everything in full, offline, so the world cannot break and can be used today in the engines and tools the creator already has. The creator writes the score; coding agents and open tools play it. The creator decides at a few fixed points (references, concept, style, review). Between them, every stage hands on explicit data or code that an agent can read and a deterministic check can test before money is spent, and the agents do the joining work a technical artist would otherwise do.

Our contributions are: SCORE as a world compiler, with its stages, canonical scene and checks (Section 3); the rules that keep generated worlds coherent and editable, chiefly the parts check, one model per object and a shared surface library (Sections 3.3 and 3.4); and four worlds of different kinds built with it, with time, cost and the faults caught before spending at every stage (Section 5).

# Related work

Genie learns an interactive environment from video [@bruce2024genie]; WorldGen generates traversable worlds from text [@wang2025worldgen]; WorldAct and WorldSculpt recover separate objects from generated worlds or video [@hu2026worldact; @niu2026worldsculpt]. SCORE ships no generated world: a world generator may enter only as an optional reference step (Section 3.6).

Holodeck places retrieved objects by solving language-model constraints [@yang2024holodeck]; SceneCraft and recursive code world models write scenes as programs and compare renders [@hu2024scenecraft; @li2026rcwm]; WorldClaw and AutoUE use agents to assemble open worlds and game code [@guo2026worldclaw; @yin2026autoue]. LEGO-Anything finds that coding agents start scenes weakly, regress while editing and judge their own geometry unreliably, and fixes this with tools rather than training [@li2026lego]. SCORE shares that stance and applies it to worlds that do not exist yet, built to a person's picks.

Infinigen and Infinigen Indoors generate worlds and rooms from procedural rules, with materials as their own generators [@raistrick2023infinigen; @raistrick2024indoors], and ProcFunc gives these generators an interface language models write with far fewer errors [@raistrick2026procfunc]. Keeping one style across generated assets is an open problem [@wu2026production; @yang2026flowscene]; Hunyuan3D Studio fixes style at the picture [@lei2025hunyuanstudio]. SCORE removes surface from generated models altogether.

# Method

## A world compiler

SCORE compiles a world once, offline, in batches; nothing is generated while it is played, and each scale of a world (a room, a planet's ground, an orbit) is its own kind of world. Table 1 lists the stages. Each stage's output is explicit, cached and checked before the next paid stage starts.

**Table 1.** Stages, their outputs and the checks that gate the next stage.

| Stage | Output | Check before the next stage |
|---|---|---|
| Concept | picked concept picture | creator's pick |
| Plan | dimensioned plan in metres | room and door checks |
| Inventory | every object as a row; children on parents | concept-density check |
| Close-ups | one clean picture per object | one object per picture |
| Shape | code builder or picture-to-3D model per kind | parts check, model check |
| Surfaces | baked maps from the shared library | palette sweep, storage budget |
| Sound | sound per surface, room and object | loudness and fault checks |
| Assembly | the OpenUSD scene and engine builds | scene check, made-only check |
| Review | shots from fixed cameras | creator's keep or send-back |

**The canonical scene.** All stages write one OpenUSD stage [@openusd] with glTF geometry [@gltf2]. Every object carries its name, kind, place in metres, collision, the library surface of each part, its sound, and tags for what a person can do with it (door, seat, terminal, airlock). The compiler owns a generated base layer and may rewrite it; the creator's changes live in edit layers above it, so a regeneration replaces the base and keeps the edits. Engines and simulators (Godot, Blender, Unreal, robotics simulators) load the same stage through thin adapters.

## Checks before spending

A fault costs nothing in the plan, cents at the picture, about €0.18 and 75 minutes at the 3D model, and an evening of the creator's time once a room is built and played. Each paid stage is therefore gated by deterministic checks on real geometry, never by an agent's judgement, and a failure sends work back one stage. Room checks cast rays for leaks through walls and roof, pieces blocking openings and pieces off their surface, in about two seconds a room. A door check requires every door to separate its two sides. A concept-density check requires every element of the concept to have an inventory row or a written reason. A model check requires closed solids with walls of at least 3 mm and fails generated boxes that lean more than 2 degrees. A palette sweep and a storage budget per room follow, and after assembly a scene check finds what floats or sinks and fails on any visible mesh the route did not make.

<!-- Fault cost: 2099 paper writing/outline.md 9f. Checks and limits: 2099 docs/bible.md items 11-12; local R&D logs progress-robust-exp.txt, progress-hub-r5.txt. -->

## Code or pipeline, one model per object

Picture-to-3D models build chunky solids well and flat panels, thin beams and openings badly; agent-written code builders are exact, light and straight, but show only the parts the agent wrote. SCORE routes each object kind by the **parts check**: a kind is built in code only when its code build shows every part its clean close-up shows, each at least 10 percent visible and none under a label. Every other kind goes through the prop pipeline: Pixal3D [@li2026pixal3d] in a cloud batch, closed into a solid, triangles set by size. Composites are split before generation, one model per real-world object: a tool board is a board carrying its tools, a console its monitors and keyboards, each made on its own.

## Surfaces and sound

Models and code give shape only. Every part takes one surface from a shared library of ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette, with wear, dirt and seed as named settings. A room has one wear setting, applied from causes: edges, foot traffic, drips. Parts of a generated model come from PartCrafter [@lin2025partcrafter], and each part takes one surface, chosen from its picture. Labels are a few decals on clear flat spots. Sound is compiled the same way: each surface carries its footsteps and impacts, each room its echo from its size and surfaces, each object its own sound, generated in one batch by MOSS-SoundEffect [@moss2026], chosen by CLAP prompt match [@wu2022clap] less measured faults, and levelled under a -3 dBTP true peak. The libraries of surfaces and sounds grow with each world and are reused in the next.

## Cloud batches and human picks

Every heavy step runs in a rented cloud machine that is deleted afterwards, records its cost per batch, and stops itself when its output grows past its expected size. The creator picks at fixed points only. Where two routes compete the pick is blind: both drawn the same way, labelled X and Y at random.

## The optional world step

A concept shows one view. An optional world step turns it into a walkable whole-room reference, so close-ups can show every object from every side and the walls the concept does not show can be filled in its style. World Labs Marble served this step in our runs; its output is never shipped, and anything derived from it is credited "Generated using World Labs".

# Implementation

SCORE runs as Python tools for planning, routing, baking, assembly and checks, with headless Blender [@blender] and rented NVIDIA L4 machines for every heavy step. Claude Code agents [@claudecode] write the plans, inventories and code builders under one creator's direction. Table 2 lists the models; each allows commercial use of its output.

**Table 2.** Models in the route.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups | paid API |
| Pixal3D [@li2026pixal3d] | picture to 3D | MIT; DINOv3 licence for its encoder |
| PartCrafter [@lin2025partcrafter] | parts | MIT |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surfaces | BSD-3-Clause |
| MOSS-SoundEffect, CLAP | sound | Apache-2.0 |
| World Labs Marble [@marble_terms] | optional world step | paid; outputs owned by paid users |

**Lessons from development.** The rules above came out of six rounds on one room, the central hub of the game 2099, each answering the creator's verdict on the last. Three findings shaped the method. Deterministic checks catch what agents miss: the first round's room checks cut light leaking through walls and roof from 1.53 percent of 5,817 rays to zero, but only walking the loaded room showed 26 old models still in it, which became the made-only check. Keeping each picture's own colours made every piece bring its own wear, so the creator judged the room messy; surfaces now come only from the library. And generated composites melted their parts together and generated boxes leaned (one locker by 13 degrees), which led to one model per object and the straightness check. The creator preferred the new route in both blind comparisons and accepted the sixth round.

<!-- 1.53% of 5,817 rays: progress-robust-exp.txt [A/B numbers]. 26 old models: progress-robust-exp.txt round three fix round. "messy": brief job-hub-r5-test.txt quoting the owner on round four. Locker 13 degrees: 2099 docs/bible.md item 11. Blind picks: progress-robust-exp.txt (round one key and quote; round two key), session record 2026-10-06T16:52Z. Accepted: issue JoeyKardolus/2099#130, 2026-10-07T16:20. -->

# Results

::: gap
**Gap: results table across worlds.** For each place of each world: wall time, cost in GPU time and picture calls, models made in code and through the prop pipeline, and faults caught before spending per stage against faults found after. Waits on world 1 being finished and reviewed by its creator (most of its places are built, none after the hub yet reviewed in play) and on worlds 2 to 4.
:::

::: gap
**Gap: one figure per world.** The picked concept beside the finished place from the concept's own camera, for the main places of each world. Waits on the same worlds.
:::

# Evaluation

::: gap
**Gap: LEGO-Bench.** Scores of SCORE on LEGO-Bench [@li2026lego], LEGO-Anything's benchmark of scenes rebuilt from pictures. Waits on the benchmark's code release and on SCORE's OpenUSD export with its Blender adapter.
:::

::: gap
**Gap: world-step ablation.** The route with and without the optional world step on the same places: inventory coverage of the concept, concept density of the built room, cost, and the creator's blind pick. Waits on the route running from the framework repository; the first internal run stopped when the game work paused.
:::

::: gap
**Gap: style coherence.** A measure of whether a room keeps one style, from rendered frames: colour distance to the place's palette per kind of source, lightness spread and ink density, set against the creator's blind picks. The measure is designed and not built.
:::

::: gap
**Gap: physics in the robotics world.** A rigged robot in the simulation world, loaded in a robotics simulator, with masses, friction and joints compiled from the scene. Waits on world 3 and on those properties in the scene schema.
:::

::: gap
**Gap: solver plugins.** Scales that are computed rather than modelled, starting with orbits through REBOUND [@rein2012rebound], wrapped as stages with the same strict interfaces. Waits on the plugin interface in the framework repository.
:::

# Limitations

Every verdict on the worlds so far is one creator's. Most models in the first world were code builders written by a coding agent, so the clean result depends on the agent as much as on the framework, and each new kind of object costs an agent's builder. Rooms built from one concept picture come out sparser than the concept, which the concept-density check catches but does not fix. Daily picture-model quotas and GPU stock, not compute cost, set the pace of a build.

<!-- 865 of 971 models were code builders: scaling-world1.tsv (local R&D log). Sparse rooms and quotas: issue JoeyKardolus/2099#130, 2026-10-07T23:04 (lab), 2026-10-08T09:18 (greenhouse, quota). -->

# Availability

SCORE is developed in the open at <https://github.com/Babon-Innovations-b-v/score> under the MIT licence. The build logs behind every reported number are published with it.

# References {-}
