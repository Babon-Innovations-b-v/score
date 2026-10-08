---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "First full draft, 8 October 2026"
abstract: |
  World models and one-shot 3D generators can now produce a convincing place from a sentence or a picture, but what they produce is hard to build on: a stream of frames, or one fused scene with no separate objects, collision, logic or rights a creator can rely on. We describe SCORE, a framework that treats world creation as offline compilation. The creator picks references, concepts and a style; coding agents and open models then turn those picks into a fixed, editable world through a sequence of stages with explicit, checkable outputs: a dimensioned plan, an inventory of objects, one generated or code-built model per real-world object, surfaces from a shared rule-based library with one wear setting per room, generated sound, and a scene an engine loads. Cheap checks run before every paid step, and every model in the route is one whose licence allows commercial use. We report the first world built this way, the game world of 2099: a Moon base, its surroundings, a Mars expedition camp and a prologue on Earth. The base's central room took six rounds; the owner picked the new route in both blind comparisons and signed off the sixth round, which also cut the room's mean frame time from 9.6 ms in the fourth round to 5.6 ms on an RTX 5080. Across 21 recorded place runs of the whole world, the per-place records count 971 models, 865 of them built in code by coding agents and 106 through a picture-to-3D pipeline, for a recorded floor of €46.67 of rented GPU time and $40.72 of picture-model calls. The same record shows where the route is weak: code builders give clean but sparse rooms, picture-colour painting produces patchy surfaces, built rooms read sparser than their concepts, and daily quotas, not compute, set the pace. Nothing here is compared with another system yet; evaluation on LEGO-Bench is future work.
---

<!--
  Draft conventions.
  - Every number is read from a file. The file is named in a comment like this one,
    next to the number. Files named "local R&D log" are the build sessions' own logs on
    the owner's machine; they are not in this repository yet.
  - [text]{.todo} marks anything not measured or not checked. It prints red in the PDF.
  - The world step (World Labs Marble in our runs) is described only as one optional step
    of the method. No result here compares it with another model or judges it on its own.
-->

# Introduction

A person who wants to make a world, for a game, a film, a simulation or a robot to train in, faces the same problem whatever tools they use: the world has to be complete, and it has to be theirs. Complete means more than looking right from one camera. Doors open, floors hold, machines sit where they can be reached, rooms have light and sound, and every object can be found, moved, replaced and given behaviour. Theirs means the creator decides what the world is, can change any part of it later without starting over, and holds the rights to all of it.

Generative models have made the first impression of a world cheap. Genie 3 turns a prompt into a world a person can move through in real time [@genie3; @bruce2024genie]. Image and video models give a convincing view of a room from one picture, and picture-to-3D models give a mesh of an object from one view [@li2026pixal3d; @xiang2024trellis]. Yet neither kind of output is easy to build on. A world model renders frames: its own announcement lists a constrained range of actions and a few minutes of continuous interaction among its limits [@genie3], and nothing it makes can be opened in an editor. A one-shot 3D scene is one fused asset; a recent paper describes such outputs as "static monolithic assets with limited editability and physical interaction" [@hu2026worldact]. Neither gives a creator a world they can keep working on.

SCORE takes the opposite approach. It treats world creation as offline compilation: heavy model work happens once, in batches, before anyone plays, and what comes out is a fixed set of files a game engine or simulator loads. The creator writes the score, and coding agents and open tools play it. The creator picks references, concepts and a style at a few fixed points. Everything between those points is a stage whose output is explicit data or code: a plan in metres, an inventory of every object, one model per real-world object, surfaces from a shared library, sound for every surface and object. Because each stage hands on something an agent can read and check, cheap checks can run before every step that costs money, and a coding agent can do the joining work that would otherwise fall to a technical artist.

This is a different bet from a world model's. A world model learns to show only what the player sees, frame by frame. SCORE builds everything in full, so that the world cannot break when the player looks somewhere unexpected and can be used today in the engines and tools people already have. Neither approach is right or wrong; they answer different needs, and world models are improving fast. What SCORE offers is the part they do not: a world that is complete, owned and editable.

This paper makes three contributions:

1. **A method.** SCORE as a world compiler: its stages, what each stage hands on, the checks that run before money is spent, and the rules that decide whether a piece is built in code or by a picture-to-3D model (Section 3).
2. **A worked world.** The first world built with it, the game world of 2099, with time, cost and the faults caught for each place, and the base's central room as a case study over six rounds with the owner's blind picks (Section 5).
3. **An honest account of the limits.** Where the route failed, what was a human pick, what a coding agent wrote and what was a hand fix (Sections 4 and 6).

The name needs one note. SCORE is not WorldScore, a benchmark for world generation [@duan2025worldscore], which we may report against; it is not score distillation in text-to-3D [@poole2022dreamfusion]; and it is not SCoRe, a reinforcement learning method for language models [@kumar2024score].

# Related work

**World models and one-shot world generators.** Genie learns an interactive environment from video and lets a user act in it frame by frame [@bruce2024genie]; Genie 3 does so in real time from a prompt [@genie3]. WorldGen generates traversable, editable worlds from text for standard game engines [@wang2025worldgen]; HY-World 2.0 generates one splat or mesh world from text or a picture [@hyworld2]; WorldAct decomposes such a monolithic world into objects after the fact [@hu2026worldact]; WorldSculpt composes per-object meshes from grounded video [@niu2026worldsculpt]. Commercial world generators such as World Labs' Marble build one world per request from text, pictures or a panorama [@marble_docs]. SCORE uses no world model as its output. A world generator can appear in it only as an optional step that produces a reference for later stages (Section 3.10).

**Agents that build scenes.** Holodeck has a language model write spatial constraints that a solver satisfies, with objects retrieved from a library [@yang2024holodeck]; LayoutGPT plans layouts with a language model [@feng2023layoutgpt]. SceneCraft has an agent write Blender code [@hu2024scenecraft], recursive code world models build a scene as a program and compare renders with a reference [@li2026rcwm], WorldClaw runs render-checking agents over a terrain [@guo2026worldclaw], and AutoUE has agents write gameplay code in Unreal Engine [@yin2026autoue]. 3D-RE-GEN turns one picture of a room into separate objects through detection, per-object generation and placement [@sautter2025regen], and SceneConductor adds a planner agent that finds inconsistencies after placement [@kim2026sceneconductor]. LEGO-Anything is the closest in spirit: a coding agent writes and revises Blender code to rebuild a scene from one picture, and its authors find three recurring failures, "weak scene initialization, regressive edits during iteration, and unreliable self-evaluation", which they address with tools rather than training [@li2026lego]. SCORE takes the same position, that an agent should be given grounded tools in place of its own judgement, but aims at worlds that do not exist yet, built to a person's picks.

**Procedural generation and surfaces.** Infinigen generates whole natural worlds from randomized rules, with materials as their own generators [@raistrick2023infinigen]; Infinigen Indoors adds a constraint language and solver for arranging rooms [@raistrick2024indoors] and articulated assets [@joshi2025articulated]. ProcFunc gives these generators a function-oriented Python interface on which vision-language models make far fewer coding errors when writing procedural materials from scratch [@raistrick2026procfunc]. MatFuse generates materials from palettes, sketches and pictures [@vecchio2023matfuse]. Studios have long shared surfaces across pieces rather than texturing each one [@olsen2015trim], and build environments from modular kits with strict footprints [@burgess2013skyrim; @ldb_modular]. SCORE's surface library is written in ProcFunc on Infinigen's shader code.

**Parts and style.** PartCrafter generates a mesh as several parts from one picture [@lin2025partcrafter]; OmniPart, HoloPart and SAMPart3D plan, complete or segment parts [@yang2025omnipart; @yang2025holopart; @yang2024sampart3d]; Point2Part partitions a shape from point prompts [@tsui2026point2part]. Keeping one style across generated objects is named as open: a survey of production-ready 3D generation notes that no large dataset carries coherent lighting, style descriptors or compatible materials across assets [@wu2026production], FlowScene notes that retrieval-based composition "often fail[s] to enforce scene-level style coherence" [@yang2026flowscene], and Hunyuan3D Studio fixes a style at the picture before any 3D is made [@lei2025hunyuanstudio]. SCORE holds style by taking it away from the generated models altogether: they give shape only, and every surface comes from one library.

# Method: SCORE as a world compiler

## Overview

A compiler turns a source a person wrote into an output a machine runs, through stages whose intermediate forms can be inspected, cached and checked. SCORE has the same shape. Its source is the creator's picks; its output is a world an engine loads; its stages are listed in Table 1. A world is compiled once, offline, in batches. Nothing is generated while the world is played, and each scale of a world (a room, a planet's surface, an orbit) is its own kind of world rather than one continuous zoom.

**Table 1.** The stages of the route as run for world 1. "Who" says what decides or does the work: the creator (a human pick), a coding agent, a model in a cloud batch, or a deterministic tool.

| Stage | Input | Output | Who |
|---|---|---|---|
| 1. References and concept | the creator's brief and reference pictures | a few concept pictures; one is picked | picture model draws; creator picks |
| 2. Dimensioned plan | the picked concept | a plan in metres: shell, doorways, walkways, floor levels | coding agent; checks |
| 3. Inventory | plan and concept | every object as a row: kind, anchor, size, count; parent and child rows | coding agent; concept-density check |
| 4. Close-ups | inventory rows | one clean picture of each object, front-on | picture model |
| 5. Code or pipeline | close-up and a code build | each kind routed to code or to the prop pipeline | parts check (deterministic) |
| 6. Shape | routed kinds | code builders; or picture-to-3D models made solid | coding agent writes builders; Pixal3D in cloud batches |
| 7. Surfaces | shapes with named parts | baked maps from the surface library, one room wear | ProcFunc recipes in cloud batches |
| 8. Sound | surfaces, rooms, inventory | footstep, impact and echo per surface and room, a sound per object | MOSS-SoundEffect in a cloud batch; loudness rules |
| 9. Assembly | everything above | the scene package an engine loads | deterministic tools; checks |
| 10. Review | shots from fixed cameras | keep, or send back one stage | creator |

## The canonical scene: a generated base layer and edit layers

A compiler needs one intermediate form every stage agrees on. For SCORE that form is a scene description with a strict schema: every object has a name, a kind, a place and turn in a stated frame, a size in metres, a collision shape, the surface of each of its parts, its sound, and tags that say what a person can do with it (a door, a seat, a terminal, an airlock). Geometry is glTF 2.0 [@gltf2]. The scene itself is designed to be an OpenUSD stage [@openusd] in two kinds of layer: a generated base layer that the compiler owns and may rewrite, and edit layers that hold the creator's own changes. Because OpenUSD composes layers, a regeneration replaces the base layer and the creator's edits survive on top of it. Engines and tools (Godot, Blender, Unreal, a robotics simulator) then load the same scene through thin adapters.

That is the design. What runs today is narrower, and we say so plainly: in world 1 the canonical form is glTF models plus one JSON layout file per place, read by one adapter, the Godot engine's [@godot]. The OpenUSD stage, its layer split and every adapter other than Godot's are [not built; the move is the next piece of work in the framework repository]{.todo}.

## Checks before spending

Every fault costs more the later it is found. A fault costs nothing in the plan, cents at the picture, about €0.18 and 75 minutes at the 3D model, and an evening of the creator's time once a room is built and played. So each paid stage is preceded by checks that are cheap, deterministic and run on real geometry rather than on an agent's judgement, and a failed check sends the work back one stage, never forward with a flag. The checks used in world 1 were:

- **Room checks** on the laid-out room's real meshes, about two seconds a room: rays that leave through walls or roof (leak), pieces in front of a real opening, pieces that do not lie on the surface they belong to, and the room's piece, triangle and lamp budget.
- **Door check:** every door must stand in a wall or partition that fully separates its two sides, read as a walk on a grid.
- **Concept-density check:** every element visible in the picked concept, cut into crops, has an inventory row or a written reason it was dropped; after the build the room is shot from the concept's own camera and compared.
- **Parts check:** a code builder may only stand in for a picture-to-3D model if its build shows every part the object's clean close-up shows (Section 3.4).
- **Model check:** every model is closed and solid with walls of at least 3 mm; a generated piece that should be square fails when its sides tilt more than 2 degrees or warp (the straightness check).
- **Palette sweep and storage budget:** every made model's colours against the room's own library palette, and a budget per room of 250 MB on disk and 640 MB of textures on the graphics card.
- **Scene check and made-only check** in the engine after install: rays that find what floats, sinks or overlaps, and a walk of the loaded scene that fails on any visible mesh the route did not make.

<!-- Check list and limits: 2099 docs/bible.md, workflow/bootstrap items 11 and 12; local R&D logs progress-robust-exp.txt, progress-hub-r5.txt, progress-modules-r6.txt; issue JoeyKardolus/2099#130 comments of 2026-10-07. -->

## Code or prop pipeline: the sorter and the parts check

Picture-to-3D models are good at chunky solids and bad at flat panels, thin beams and things with openings: in the base's central room they made panels about as deep as they were wide, beams 3 to 10 times too thick, and holes filled in.

<!-- Panel, beam and hole faults; fault cost per stage: 2099 paper writing/outline.md, sections 9e and 9f (sixth pass). -->
 Coding agents are the reverse. A code builder is exact, light and straight, but it shows only the parts the agent thought to write. So each object kind is routed one way or the other, and the rule for it changed three times in the case study (Section 5.1). The rule that held is a check, not a list of shapes: a kind may be built in code only when its code build, rendered from in front, shows every part its clean close-up shows, each at least 10 percent visible, with no printed label over a part. Every other kind goes through the prop pipeline: a close-up picture, Pixal3D [@li2026pixal3d] in a cloud batch, the paper-thin output closed into a solid, its triangles set by its size, and the straightness check.

## One model per object

A tool board with twenty tools on it, generated as one model, melts the tools into the board; a console generated as one piece fuses desk, screens, keyboards and cables. SCORE therefore splits composites before anything is generated: one model per real-world object. A parent row (the board, the desk) carries child rows anchored on it (each tool, each monitor), and each child is routed and made on its own. In the central room the tool board became a code-built board with pegs and an outline printed under each tool from that tool's own silhouette, carrying 26 tools.

<!-- Composite split and the 26 tools: 2099 docs/bible.md item 11, rounds five and six; issue #130 comment 2026-10-07T15:55. -->

## Surfaces: one library, one room wear

Generated models carry their own textures, and each brings its own idea of what worn steel looks like; side by side they read as a mix. SCORE keeps shape and surface apart. Models and code give a piece its shape only, and every part names one surface from a shared library. Each surface is a ProcFunc function [@raistrick2026procfunc] built on Infinigen's shaders [@raistrick2023infinigen], coloured only from the place's palette tokens, with wear, dirt and seed as named settings, baked in the cloud to the maps the engine needs at the texture density each piece needs. A room has one wear setting, and wear comes from a cause: edges, feet near the floor, drips under pipes. Labels and notes go on top as a few decals, each on a clear flat spot. On a generated model, the surface of each part is chosen from its picture by PartCrafter parts [@lin2025partcrafter] laid onto the Pixal3D shape: the picture's colour picks which library surface a whole part takes, never the colour of a single face.

The library for world 1 holds 71 variants in 12 families (painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light and print) from 14 recipes, grown later with Earth surfaces such as plaster, tile, terrazzo, floorboards, rusted steel and wet asphalt.

<!-- 71 variants, 12 families, 14 recipes: local R&D log progress-robust-exp.txt, round two. Earth recipes: issue #130 comment 2026-10-07T17:40. -->

## Sound

Sound is part of the world, not an afterthought, and it is compiled the same way. The world's data says what everything sounds like in three layers: each surface carries its footstep, impact and scrape; each room works out its echo from its size and surfaces; each object's inventory row names its own sound. Every sound is generated in one cloud batch by MOSS-SoundEffect v2.0 [@moss2026], four takes each, and the take is chosen automatically by its match to its prompt under LAION's CLAP model [@wu2022clap] less measured faults (clipping, unsteady loops, bad joins). Every take is levelled to one loudness per kind under a true peak of -3 dBTP before it can play. A creator may swap any sound on a review page; picking is optional.

<!-- Sound route: 2099 docs/bible.md item 12. -->

## Cloud batches and cost control

Every heavy step runs in a rented cloud batch, never on the creator's machine: picture-to-3D, part splitting, surface bakes, sound and, by the end of world 1, the engine's own tests, shots and frame-time bench. Machines are rented for a batch and deleted after it. Each batch records its cost in a ledger, and each place's run records its wall time, its spend and the faults caught before and after spending. A step that grows past its expected size stops itself: when closing a generated piece into a solid threw spikes 60 m long, the step gained a check that stops the job once the copy's box grows more than 3 percent past the model's.

<!-- The 60 m spikes and the 3 percent box check: local R&D log progress-robust-exp.txt, round three, 20:09 and 20:13. -->

## Human picks

The creator decides at a few fixed points and nowhere else: the references, the concept, the style, and the final review of each place. Where two routes compete, the review is blind: both sides are drawn the same way (same renderer, light, camera and size), labelled X and Y at random, and the key is kept out of the page until the pick is made. A page that cannot be drawn the same way says that it is not blind. Agents may make interim picks to keep a run moving, but each such pick is marked on its page as the agent's, so the creator can reverse it.

## The optional world step

A concept is one picture from one angle. It shows two or three walls, and each object from one side. An optional world step turns the picked concept into a walkable reference of the whole room, from which close-ups of every object can be taken from any side and the walls the concept does not show can be filled in the same style. In our runs this step used World Labs Marble. Nothing a world step makes is shipped: it is a reference for later stages, never part of the world. Where its outputs or anything derived from them are shown, they carry the credit "Generated using World Labs".

The world-1 results in Section 5 were all produced **without** this step: after the route change of 7 October, close-ups were cropped from the concept picture directly. Whether the route makes fuller rooms with the world step than without it is [not measured; an internal run on one room was started on 8 October and stopped when the game work paused]{.todo}.

<!-- Route ran without the world step from 2026-10-07: coordinator's account in the session record of 2026-10-08 ("since the method change, agents have been cropping close-ups straight from the concept picture"); world-step test: local R&D log progress-worldstep.txt. -->

# Implementation

**Code and compute.** World 1 was built inside the game's own repository, 2099, as Python tools for the route (sorter, plan, layout, bake, install, checks), Godot-side checks, and cloud runners for Scaleway machines with NVIDIA L4 cards. The route's code moves to the SCORE repository next; [this paper's repository does not hold it yet]{.todo}. Blender 5.0.1 runs headless in the cloud for every bake [@blender]. The engine is Godot [@godot]; the frame-time bench runs on an RTX 5080, and cloud benches on L4 cards are converted with a measured ratio of 3.47.

<!-- 3.47 ratio: issue #130 comment 2026-10-07T21:57. -->

**Coding agents.** The work was done by Claude Code agent sessions [@claudecode] directed by one person, the owner. During the world-1 build up to twelve agents ran at once, about one per place, coordinated by one overseeing session.

<!-- Twelve agents: session record 2026-10-08T00:28Z ("All twelve agents are back to work"). -->

**Models and their licences.** Every model in the route must allow commercial use of what it makes. Table 2 lists the models world 1 used and the licence each was used under; licences were read for the clauses that decide commercial use, not in full, and this is not legal advice.

**Table 2.** Models and services in the route, with licences as read by the build sessions.

| Model or service | Used for | Licence or terms |
|---|---|---|
| Nano Banana Pro (Gemini 3 Pro Image) [@nanobananapro] | concepts, close-ups, ground skins | paid API; [Gemini API terms on output ownership to be quoted]{.todo} |
| Pixal3D [@li2026pixal3d], via image-to-3dlab [@imageto3dlab] | picture-to-3D shape | MIT code and weights; bundled DINOv3 encoder [@simeoni2025dinov3] under the DINOv3 Licence |
| PartCrafter [@lin2025partcrafter] | part boundaries for painting | MIT code and weights; its non-commercial background remover patched out |
| Depth Anything V2 Small [@yang2024dav2] | fine relief on planned ground | Apache-2.0 (the Base and Large sizes are non-commercial and not used) |
| ProcFunc and Infinigen shaders [@raistrick2026procfunc; @raistrick2023infinigen] | surface library | BSD-3-Clause |
| MOSS-SoundEffect v2.0 [@moss2026] | sound | Apache-2.0 code and weights |
| LAION CLAP, larger\_clap\_general [@wu2022clap] | choosing sound takes | Apache-2.0 |
| World Labs Marble [@marble_terms] | optional world step only | paid; outputs owned by paid users (§3.3); attribution on request (§3.7) |
| Claude Code [@claudecode] | coding agents | paid subscription |

Earlier rounds of the game's props also used FLUX.2 klein 4B (Apache-2.0) [@flux2klein], and the game's people use Kimodo [@rempe2026kimodo] and SAM 3D Body [@yang2026sam3dbody]; neither is part of the world-1 route. Two candidates were ruled out on licence: NVIDIA's Lyra 2.0, whose weights are for internal research only, and Hunyuan3D 2.1, whose licence does not apply in the European Union.

<!-- Licences: local R&D logs progress-robust-exp.txt [0 sources] and [splitter]; progress-worldstep.txt STEP 1; 2099 docs/bible.md items 11-12; 2099 paper material 07-sources.md. -->

**What was automatic, what an agent wrote, what was a hand fix, what was a pick.** We separate these because a reader cannot judge the route otherwise.

- *Automatic:* the picture-to-3D models, part splitting, the solid step, surface bakes, sound generation and take choice, all checks, install and the engine's tests.
- *Written by a coding agent:* every code builder. In the central room's final round, 86 of its 98 models were built in code, and a Claude agent wrote a builder for each kind by looking at its close-up. Across world 1, 865 of the 971 models in the scaling table were built in code. This is the framework's design ("agents build"), but it is a large part of why the rooms look clean, and it is not a picture-to-3D result.
- *Hand fixes:* some generated objects (a lamp, a headset, a microscope, a radio) were turned to face the right way by eye; in round five a few labels were placed by hand before a rule replaced that; agents fixed the faults the checks found, and a few were judged by eye from shots.
- *Human picks:* the owner's blind picks, his verdicts on each round, his rulings that changed the route, and the concept picks. Many concept picks in world 1 were the coordinating agent's, marked on their pages for the owner to change.

<!-- 86 of 98: 2099 docs/bible.md item 11, rounds five and six. Hand turns and labels: session record 2026-10-07T16:33Z (framework audit). 865 and 971: sum of models_code and models_pipeline over scaling-world1.tsv (local R&D log), 21 rows. -->

# Results

## Case study: the central room in six rounds

The hub is the middle module of the Moon base, where the walkway tubes meet: a twelve-sided shell over a sunken pit, with four tube hatches and an airlock. Its structure came from a cutaway the owner picked from twenty drawn by a picture model from reference pictures he kept (Figure 1). It was then rebuilt six times between 6 and 7 October 2026, each round answering what the owner found in the last. Table 3 gives the rounds; the numbers are from the build logs.

![The picked concept for the hub, cutaway C12: a twelve-sided shell over a sunken pit. Drawn by Nano Banana Pro from reference pictures the owner kept; picked by the owner from twenty cutaways. This picture fixes the room's structure; it is not shipped.](figures/hub-concept-c12.jpg){width=90%}

**Table 3.** The hub's six rounds. Cost is rented GPU time (€) and picture-model calls ($). Frame time is the mean on the RTX 5080 at night, 1600×900.

| Round | What changed | Owner's verdict | Cost | Frame time |
|---|---|---|---|---|
| 1 (slice of two walls, A/B) | surface library (11 surfaces), sorter by shape, room checks, PartCrafter parts | blind pick for the new route: "Y looks much cleaner" | €0.88, $0 | 7.81 ms against 7.53 (whole hub, one slice changed) |
| 2 (slice, A/B) | library to 71 variants, screens and labels as code parts, roof check, shared texture sets | blind pick for the new route again | €1.70, $0 | 8.05 ms against 8.24 |
| 3 (whole hub) | the route end to end: 74 models, 457 pieces | a move made without asking; 26 old models still showing; Chinese labels; floor fittings "smacked on" | €1.67 with its fix round, $0 | 6.78 ms (old hub 9.22) |
| 4 (whole hub) | code only for plain plates, pipes and trims; detail through the pipeline with the picture's own colours laid over | detail back, but "pretty much all of this became messy", "inconsistent with the rest of the room" | €8.50, $5.09 | 9.6 ms |
| 5 (eight pieces, blind A/B) | method B: shape only from the pipeline, every surface from the library, code or pipeline by the parts check | B wins for the door, notice board and porthole; tool board, locker and console still wrong | €0.21, $0 | not run |
| 6 (whole hub) | method B everywhere; composites split, one model per object; straightness check | "this looks amazing, I have no negative feedback" | about €3.48, $1.07 | 5.6 ms (round four 9.6) |

<!-- Round 1: progress-robust-exp.txt [A/B numbers], [blind pick key]; owner quote at "== ROUND TWO". Round 2: progress-robust-exp.txt [A/B round two], [spend round two]; key "X = B"; session record 2026-10-06T16:52Z "X was the new route again". Round 3: progress-robust-exp.txt round three and fix round; issue #130 comment 2026-10-06T22:34. Round 4: progress-hub-r4.txt; issue #130 comment 2026-10-07T05:29; owner quotes in brief job-hub-r5-test.txt. Round 5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt ("B wins door/notice/porthole; toolboard, locker, console still bad"). Round 6: progress-hub-r5.txt ROUND SIX; issue #130 comments 2026-10-07T15:55 and 16:20 (owner quote). -->

Three findings come out of the six rounds.

**Grounded checks catch what an agent misses, and miss what only play shows.** Already in round one the room checks found the faults the owner had seen in the old hub: light escaping through walls and roof fell from 1.53 percent of 5,817 rays to zero, a box that covered the porthole was moved 0.5 m by the placement check, and in round two the surface check found all nine roof pieces the owner had seen hanging below the roof. Colour noise inside each surface fell from a median of 31.1 to 3.2 percent. But the checks did not find what the owner found by walking the room in round three: that 26 old models were still showing, because the claim "every piece is made" had covered only the kit and not what the engine actually loaded. A check that walks the loaded scene (the made-only check) was added, and found 26 before the fix and none after.

<!-- 1.53% of 5,817 rays, 0.50 m, colour noise 31.1 to 3.2%: progress-robust-exp.txt [A/B numbers]. Nine roof pieces: [surface check]. 26 not-made: round three fix round. -->

**The split between code and pipeline is the hard decision, and a list does not make it.** Round three routed by shape and sent the furniture to code, and the owner found the old pieces' detail gone. Round four answered with an allow-list (code only for 19 plain kinds) and laid each picture's own colours over the library surfaces; the detail came back, but every piece brought its own rust and stains, and the room read as messy. Round five replaced the list with the parts check and took the picture's colours away entirely; the owner's blind picks favoured that method wherever its pieces were built well, and the three that still failed had one thing in common: each was a set of objects generated as one model, or a box the picture-to-3D model could not keep straight. Round six answered with one model per object and the straightness check (the round-four locker leaned 13 degrees; a generated radio 11, so it moved to code). Figure 2 shows the tool board in rounds four and six.

![The hub's tool board up close in round four (left) and round six (right), same camera and build. Left: one generated model with the picture's own colours laid over the library surfaces. Right: a code-built board with outlines printed from each tool's silhouette and 26 tools, each its own model, with library surfaces only. In-game shots from 2099.](figures/hub-toolboard-r4-r6.jpg){width=100%}

**Consistency and cost moved together.** Round six's room drew 0.45 million triangles against round four's 1.96 million, ran at 5.6 ms a frame against 9.6, and took 187 MB on disk against 487. The gain came from shared texture sets, triangles set by an object's size, and code builders for the room's fittings. Small objects need a floor: at the first size budget the pliers' outline went angular up close, so every small generated object now gets at least 5,000 triangles.

<!-- 0.45 M vs 1.96 M, 5.6 vs 9.6 ms, 187 vs 487 MB, 5,000 triangles: issue #130 comment 2026-10-07T15:55; 2099 docs/bible.md item 11. -->

Over the six rounds the hub's route cost about €16.44 of rented GPU time and $6.16 of picture calls, and took about 23 hours of wall-clock time. [Wall time per round is read from first and last log lines and includes waiting; an exact figure needs the logs re-read]{.todo}. The concept stage before round one (twenty cutaways, the owner's pick) is not included.

<!-- €16.44 = 0.88 + 1.70 + 1.67 + 8.50 + 0.21 + 3.48; $6.16 = 5.09 + 1.07 (Table 3 sources). Wall time: R1 about 2.3 h, R2 3.3 h, R3 3.5 h + fix round 1.8 h, R4 6.7 h, R5 0.7 h, R6 4.4 h, from progress-robust-exp.txt, progress-hub-r4.txt, progress-hub-r5.txt and the session record. -->

## World 1, place by place

After the hub was signed off, round six's method became the route for every place, and the rest of world 1 was built in parallel, about one agent per place, between 7 October evening and 8 October noon, when the owner paused the game work. Table 4 is the per-place record the agents kept.

**Table 4.** Time, cost and models per place for world 1 after the hub. Wall time includes waiting for cloud machines, quota resets and two usage-limit stops; several places shared one agent, and a shared time or cost is marked. Costs are floors from the agents' own notes, not reconciled with the cloud bill. Models are counted as built in code / made through the prop pipeline.

| Place | Wall time (min) | Cloud € | Pictures $ | Code / pipeline |
|---|---|---|---|---|
| Moon ground, whole Moon (round two) | 360 | 0.08 | 5.29 | 0 / 0 |
| Old station | 253, shared with the wreck | 4.93 | 3.22 | 10 / 14 |
| Wreck | shared | 2.40 | 2.68 | 3 / 13 |
| Lab, round one | 367 | 5.55 | 2.68 | 53 / 14 |
| Lab, round two (not shipped) | — | 2.30 | 1.47 | 54 / 22 |
| Workshop | 519 | 2.80 | 3.35 | 110 / 8 |
| Greenhouse | 990 | 4.60 | 2.13 | 157 / 3 |
| Crew habitat | 530, shared by three | 1.31 | 1.34 | 108 / 2 |
| Airlock | shared | 0.79 | 0.13 | 81 / 1 |
| Walkway tubes | shared | 0.14 | 0 | 25 / 0 |
| Prologue flat with balcony | 633, shared by two | 4.69 for both | 2.41 for both | 35 / 10 |
| Prologue stairwell | shared | shared | shared | 44 / 1 |
| Street (not shipped) | 1039, shared by three | 1.42 | 1.74 | 45 / 2 |
| Square (not shipped) | shared | 2.05 | 1.07 | 75 / 2 |
| Launch view (not shipped) | shared | 0.75 | 0.40 | 4 / 1 |
| Mars ground | 513 | 0.64 | 1.58 | 0 / 0 |
| Mars camp grounds, two parts | 271 + 280 | 2.05 + 0.77 | 1.04 + 0.27 | 2 / 8 |
| Mars camp habitat, two passes | 586 + 445 | 5.20 + 1.60 | 1.21 + 0 | 59 / 5 |
| Garage and hangar (paused) | — | about 2.60 | 8.71 | — |
| **Total, 21 rows** | | **46.67** | **40.72** | **865 / 106** |

<!-- Every cell: scaling-world1.tsv (local R&D log), read 2026-10-08. Totals summed over its 21 rows; the garage row's "~2.60" counted as 2.60; rows marked "shared" counted once. -->

Two things stand out. First, the cost of a place is small next to the time it takes: most places cost a few euros of GPU time and a few dollars of pictures, while their wall time ran to many hours, mostly waiting. Second, the route leaned heavily on code: 865 of 971 models were code builders. In some rooms that gave clean, convincing pieces (the greenhouse's console, tank and racks are all code), but in the lab the same pull gave plain and sparse results, and the owner's view is that code builders are clean but neither scale nor are robust.

<!-- Owner on code builders: session record 2026-10-08T09:27Z ("I've also noted your view on code builders: clean, but not scaling or robust"). -->

**The Moon's ground, the old station and the wreck.** The ground round the base is planned rather than seeded: a dimensioned plan in code, a diorama picture, plan heights following it, a skin painted over the plan, fine relief from Depth Anything V2 Small, and boulders from Pixal3D. Its first round holds 11 named craters of 9 kinds and 140 small ones round the base's flats and paths; the owner preferred it to a crater generated with Infinigen ("new is a lot better"), but that comparison was not blind, because the two were drawn in different renderers and he could tell them apart in every view. Round two planned the whole Moon over the six faces of a cube, with 27 named far craters, about 1,300 small ones and 7,000 rocks, and blended the faces so the median step at an edge fell from 0.48 m to 0.02 m. It also found an old bug that had flattened every crater rim. The old station and the wreck were built on the signed-off route (Figures 3 and 4); the owner signed both off on first sight ("it just looks great").

<!-- Ground round one: issue #130 comments 2026-10-06T21:05 and 21:44; blind failure: progress-moonground.txt 23:44 and session record 2026-10-06T21:43Z. Round two: issue #130 comment 2026-10-07T18:14. Old station and wreck: issue #130 comments 2026-10-07T21:08 and 21:16. -->

![The old station on the Moon: a lived-in lander joined by walkway tubes to a torn first module and a shut lab, with sandbags, masts and a radiator. 14 objects through the prop pipeline and 10 plain pieces in code, on the planned ground. In-game shot from 2099.](figures/old-station.jpg){width=100%}

![The wreck: a rocket broken in two with a work lamp burning in the break. 13 objects through the prop pipeline and 3 code-built cables. In-game shot from 2099.](figures/wreck.jpg){width=100%}

**Base modules, prologue and Mars.** The habitat, airlock and walkway tubes, the lab, workshop and greenhouse were pushed with their checks green; the owner's in-game test of them is [pending]{.todo}. The owner judged the lab's first build to have "lost a massive amount of detail" against its concept; that gave the route its concept-density check, and the lab's second round, mapped element by element to its concept, was not finished before the pause. The prologue's flat and stairwell were pushed; its street, square and launch view were built but not pushed, because one scene-check finding was still open. On Mars, the ground round the camp and the camp's two habitat domes were pushed; the domes were first built larger than their concepts (13.9 and 11.4 m across against about 10 and 9 m) and read sparser, so they were shrunk to the concepts' size; the camp grounds still fail the density check while five close-ups wait for the picture quota.

<!-- Lab: issue #130 comment 2026-10-08T10:13:50; progress-place-lab.txt ROUND TWO. Prologue: issue #130 comments 2026-10-08T03:12 and 10:13:19. Mars: issue #130 comments 2026-10-08T02:45, 03:31, 10:11. -->

**Sound.** Every sound the game names, 61 in all, was generated in one batch: 244 takes in 123 minutes on one rented L4 for €1.61, each chosen by its prompt match less measured faults. The owner listened and kept most of them, but went back to earlier recordings for breathing in the helmet, the sliding door and footsteps on steel. A prompt-match score did not foresee that.

<!-- 2099 paper writing/status.md, seventh pass, later; session record 2026-10-06T17:39Z and 18:06Z. -->

**Faults caught, before and after spending.** Every place recorded the faults its checks caught before money was spent and those found afterwards. Typical faults caught before spending were labels voted onto the wrong material by a dusty picture (one lander came out 98 percent sandbag), walls under 3 mm, a torn leg 2.4 m long against a 1.4 m piece limit, close-ups that drew the whole room instead of one object, and a door in a partition one could walk around. Typical faults found afterwards were pieces standing up where they should lie (an apron as a 4 m wall, cables as fences), shots taken at night because a Martian day is longer than the bench assumed, and rooms sparser than their concepts. [A count of faults per check, before and after spend, over all places needs the free-text columns of the scaling table coded by hand]{.todo}.

<!-- Examples: scaling-world1.tsv columns faults_caught_before_spend and faults_after; issue #130 comments 2026-10-07T21:08, 2026-10-08T01:14. -->

## What failed, and why

- **Patchy surfaces from picture colours.** Choosing each face's surface by its picture colour lets shade and shadow flip faces between surfaces, which bakes as dark blotches. Parts as the painting unit, one surface per part with the picture only choosing which, is the fix; it was being built when the work paused.
- **Sparse rooms.** Built rooms read sparser than their concepts: inventories kept the main objects and dropped the wall equipment, and a concept shows only two or three walls. The concept-density check catches it; the world step is meant to fill the walls a concept does not show, and is untested here.
- **Quotas, not compute, set the pace.** The picture model's shared daily cap (250 pictures) ran out within half an hour of its reset more than once, and close-ups waited overnight; GPU stock ran out in every zone at least once.
- **The agents' own errors.** An agent moved the console without asking; a claim that every piece was made was false; one blind page was not blind. Each became a rule or a check, but each first cost a round of the owner's attention.

<!-- Patchy surfaces: session record 2026-10-08T09:27Z; progress-paint.txt. Quota: issue #130 comment 2026-10-08T03:31 and 09:18; GPU stock: progress-robust-exp.txt [cloud stock]. -->

# Limitations

This is one owner, one world and a few days of work, and it has no comparison: nothing here was run against another system or on a shared benchmark, so no claim is made that SCORE makes better worlds than anything else. Every verdict on the result is the owner's, from pages and play, and most were relayed through an agent's transcript rather than written by him. Two of the hub's picks were blind; the ground's was not, and most of world 1's concept picks were an agent's.

The route is not yet what this paper describes as its design. The canonical OpenUSD scene with edit layers is not built; the only engine adapter is Godot's. Code builders written by a coding agent made most of the models, which says as much about the agent as about the framework, and they do not scale well: each kind needs an agent to write and check a builder. Painting by picture colour still produced patchy surfaces when the work stopped. Rooms came out sparser than their concepts. Costs are floors from the agents' notes and not reconciled with the cloud bill, wall times include queues and usage-limit stops, and the creator's and the agents' own time is not costed. Several steps still had a hand in them: turning some objects to face the right way, a few labels, and fixes to faults the checks found. Licences were read for their commercial clauses only, and none of this is legal advice. The draft itself was written by a coding agent from the build logs and checked by the owner [still to be checked]{.todo}.

# Future work

**The framework as its own code.** Move the route out of the game into this repository, engine-agnostic, with the canonical scene, its edit layers and adapters for Godot and Blender.

**More worlds.** World 1 is one kind of world. The next three are chosen to differ from it and from each other: a stylised underwater world, a physically accurate simulation world for humanoid or custom robots, which needs masses, friction and joints and an export a robotics simulator loads, and a third-person fantasy world.

**Solvers as plugins.** Some scales of a world are not modelled but computed. A planet's orbit, a cell's chemistry or a vehicle's dynamics belong to established open solvers; SCORE would wrap them as stages with the same strict interfaces, licence permitting, starting with REBOUND for orbital dynamics [@rein2012rebound].

**Evaluation.** Run the framework on LEGO-Bench, LEGO-Anything's benchmark of 208 images from 104 scenes [@li2026lego] [figures read through a summarising fetch; recheck against the paper]{.todo}, once its release allows, and measure the route with and without its optional world step as an ablation of the method.

# Availability

The framework and this paper are developed in the open at <https://github.com/Babon-Innovations-b-v/score> under the MIT licence. The route's code currently lives in the game's repository and moves here next. The build logs this draft cites are on the author's machine and [will be published with the framework, stripped of keys and account identifiers]{.todo}. Concepts and in-game pictures in this paper are the authors' own outputs from the models named in Table 2.

# References {-}
