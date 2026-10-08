---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 8 October 2026"
abstract: |
  World models and one-shot 3D generators produce a convincing place from a sentence or a picture, but not a world a creator can build on: a stream of frames, or one fused scene without separate objects, collision, logic or clear rights. SCORE is a world generation framework that joins many open vision foundation models, procedural tools and coding agents into one route from a creator's picks to a complete world in the creator's own engine. Every object is its own model, every surface comes from one shared rule-based library, sound is generated for every surface, room and object, and every model in the route allows commercial use of its output. The work runs offline in cloud batches through stages whose outputs are kept, so a weak result can be traced to the stage that caused it, rerun or fixed there, and regenerated without losing the creator's edits. Deterministic checks gate every paid step, and the creator decides the look, the concept and the style and reviews each place with tools the framework supplies. We describe the framework and apply it to four worlds of different kinds.
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main body: the core contribution. Specifics (thresholds, budgets, settings, history) are in
    the appendix.
  - Every number is read from a file named in a comment beside it. "Local R&D log" means the
    build sessions' own logs, to be published with the framework.
  - The world step (World Labs Marble in our runs) is one optional step; no result compares it
    with another model or judges it on its own.
  - Sources of the ideas: the 2099 paper notes (docs/papers/harmonizing-vision-foundation-models/,
    README, outline, material/01-11), the owner's paper notes (playtest3/paper-notes-owner.txt),
    the 2099 bible items 11-12 and CONTEXT.md, the R&D logs in playtest3/.
-->

::: gap
**Gap: Figure 1, teaser.** Four worlds made with SCORE (the game world of 2099, a stylised underwater world, a simulation world for robots, a third-person fantasy world), each as its picked concept beside the finished world in its engine. Waits on the four worlds being finished and accepted by their creators.
:::

# Introduction

Interactive 3D worlds are the material of games, film and embodied AI, where agents are trained and tested in simulators [@yang2024holodeck]. Building one is still expensive: every object must be modelled, surfaced, placed, given collision and behaviour, lit, given sound and kept in one style, and the world must stay editable as the project changes. Generative models promise to take over much of this work, but the people who would use them are wary: in GDC's 2026 survey, 36 percent of game workers used generative AI at work and 52 percent thought it was hurting the industry [@gdc2026survey]. Taking over the work is not enough; a tool has to leave the creator the author of the result, with the rights to it.

Two lines of research generate the world itself. Learned world models generate it as frames: Genie learns an interactive environment from video [@bruce2024genie], and Genie 3 renders a world a person can move through in real time, with a constrained range of actions and minutes of continuous interaction among its stated limits [@genie3]. Nothing they produce can be opened in an engine or an editor, and the world exists only as far as the player looks. 3D world generators produce geometry instead. WorldGen turns a text prompt into a traversable scene for standard game engines [@wang2025worldgen] and HY-World 2.0 turns text or a picture into one splat or mesh world [@hyworld2], but such outputs are mostly "static monolithic assets with limited editability and physical interaction" [@hu2026worldact], which WorldAct and WorldSculpt address by recovering separate objects after the fact [@hu2026worldact; @niu2026worldsculpt]. In both lines generation is one shot: when part of the result is wrong, the creator can regenerate or repair the whole, but cannot see which step limited it or change that step alone.

A third line keeps the world explicit. Infinigen and Infinigen Indoors build every asset from procedural rules, with materials as generators of their own, which yields real geometry and full control, but only the content those rules describe [@raistrick2023infinigen; @raistrick2024indoors]. Holodeck has a language model write layout constraints over retrieved assets [@yang2024holodeck], and SceneCraft, recursive code world models, WorldClaw and AutoUE let agents write scenes or whole games as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue]. LEGO-Anything shows what such agents need: rebuilding a scene from one picture, coding agents start weakly, regress while editing and judge their own geometry unreliably, and grounded tools rather than further training close much of that gap [@li2026lego]. These systems rebuild existing scenes or draw on fixed asset libraries.

Meanwhile the parts a world needs can each be read out of pictures by open models. Vision foundation models, which learned the world from images as language models learned it from text [@oquab2023dinov2], now turn a picture into a 3D shape aligned to its pixels [@li2026pixal3d], a mask per named object [@carion2025sam3], depth in metres [@wang2025moge2; @yang2024dav2], the parts of an object [@lin2025partcrafter] or a human body [@yang2026sam3dbody], and a sentence into motion [@rempe2026kimodo] or sound [@moss2026]. Most of them hand on pictures, masks, depths or meshes rather than their inner features, so a coding agent can join them like tools. What none of them keeps is one style across objects made by different models, a problem the field names as open [@wu2026production; @yang2026flowscene] and that Hunyuan3D Studio addresses only at the input picture [@lei2025hunyuanstudio].

SCORE harmonises these models into one world generation framework. Its name states its aims: worlds that are **complete** (every object, surface, light and sound exists wherever the player looks), **owned** (the creator decides what the world is, edits it in the tools they already use and holds the rights, because every model in the route allows commercial use of its output), **responsive** (objects collide, doors open, terminals and seats work), and that may be any kind of **environment**, real or made up. Instead of competing with procedural tools, part splitters or world generators, SCORE takes them in as building blocks wherever their licences allow. And instead of one shot, it works the way studios make worlds: in stages, with the creator deciding the look, the concept and the style, and coding agents and models doing the work between those decisions. Every stage's output is kept, so the work is retraceable: when a result falls short, the creator can see whether the close-up, the 3D shape or the surface limited it, rerun or fix that stage alone, and regenerate everything downstream with manual fixes kept. Cheap deterministic checks run before every paid stage, so faults are caught where they cost least. To our knowledge, no other openly available world generation work joins vision foundation models into engine-ready scenes built from reference pictures, steered by a person's choices at each step, on models that all allow commercial use; Infinigen, open but procedural rather than picture-driven, and WorldSculpt, open but a single reconstruction step without engine output, come closest.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Hand-off pattern: material/11-vision-foundation-models.md. -->

This paper makes three contributions:

- **The SCORE framework:** staged, retraceable generation from a creator's picks into one canonical scene with a generated base layer and the creator's edit layers (Section 2).
- **The mechanisms that make its worlds coherent and cheap to get right:** checks before spending, a parts check with one model per real-world object, shape and surface kept apart in shared libraries, and review tools for the creator (Section 2).
- **Evidence across four worlds of different kinds**, with time, cost and faults caught before spending at every stage, and an evaluation on a shared benchmark (Sections 3 and 4).

# Methods

A world in SCORE is generated once, offline, in cloud batches, from the creator's picks for each place: references, a concept picture and a style. One world spans the scales its story needs (the game world of 2099 holds rooms, the ground of the Moon and the ground of Mars); scales far from those, such as galaxies or cells, make worlds of their own with their own solvers. The output is one canonical scene, an OpenUSD stage [@openusd] with glTF geometry [@gltf2], in which every object carries its kind, place in metres, collision, the surface of each part, its sound, and tags for what a person can do with it, such as door, seat, terminal or airlock. Engines, Blender and robotics simulators load it through thin adapters. The framework writes a generated base layer; the creator's own changes live in edit layers above it.

**Stages.** Between picks and scene, coding agents and open models work through a fixed sequence of stages. The concept is drawn by a picture model from reference pictures the creator chose, never from words alone, because words give generic shapes; pictures meant for 3D are drawn with a level, telephoto camera so the models built from them stand straight. A dimensioned plan in metres then fixes scale and access (walkways, a standing spot at every work place, every level reachable) before anything else is drawn, since concepts come out at doll-house scale. The inventory lists every element of the concept as a row with its kind, anchor, size and count, as an exhaustive partition of the concept: nothing is made or placed that is not a row, and no element is dropped without a written reason. Then follow one clean close-up picture per object, a shape for each object, its surfaces, its sound, and assembly. Each stage's output is kept. The creator can therefore trace a weak result to the stage that caused it, rerun or hand-fix that stage alone, and regenerate everything downstream; regeneration replaces the base layer and keeps every edit. The libraries of surfaces and sounds grow with each world and are reused in the next, so work done for one world is not lost to the next.

Large outdoor places follow the same pattern at their own scale. A dimensioned plan places the flats and paths a place needs, a diorama picture drawn over the plan sets its landforms, heights follow the picture, a skin is painted over the plan with fine relief from monocular depth [@yang2024dav2], and rocks are single generated models, all built directly on the world's own curved ground. Real height data serves only to test this route, never as its source, because worlds may be made up.

**Checks before spending.** Every stage that costs money is preceded by deterministic checks on real geometry rather than an agent's judgement, because a fault costs nothing in the plan, cents at a picture, tens of cents and an hour at a 3D model, and an evening of the creator's time once a place is built. The plan is checked for leaks, blocked openings, pieces off their surface and doors that do not separate their two sides; the inventory against every element of the concept; each model for being closed, thick enough and straight; the surfaces against the place's palette and budget; and the assembled scene for anything floating or sinking and any visible mesh the route did not make (Appendix D). A failure sends the work back one stage, never forward with a flag.

<!-- Fault cost per stage (€0.18 and 75 minutes at the model): 2099 paper writing/outline.md 9f. Doll-house scale and dimensioned plan: 2099 paper README, "The hub"; memory project-scene-workflow. Exhaustive partition: memory project-scene-workflow (concept density, 2026-10-08). Terrain route: issue #130 comments 2026-10-06T21:05 and 19:33; memory feedback-framework-absorbs-tools. -->

**Code or generation, one model per object.** The shape stage decides, per kind of object, between a code builder written by a coding agent and a generated model. Picture-to-3D models build chunky solids well and flat panels, thin beams and openings badly, making panels about as deep as they are wide and beams several times too thick; code builders are exact and straight but show only the parts the agent wrote. The **parts check** settles it: a kind is built in code only when its build shows every part its close-up shows, and is otherwise generated from the close-up with Pixal3D [@li2026pixal3d] and made solid. Composites are split in the inventory, one model per real-world object, so a console is a desk carrying its monitors and keyboards rather than one fused mesh, and moving parts such as doors and hatches are made as parts of their own so they can move. Generated models keep their full detail near the player: triangles follow an object's size with a floor for small objects, and distance is handled by the engine's level of detail, never by cutting the mesh.

**Shape and surface apart.** Shapes carry no surface of their own. Every part takes one surface from a shared library of ProcFunc functions [@raistrick2026procfunc] built on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette, with wear, dirt and seed as settings and one wear setting per room, applied from causes such as edges and foot traffic, so every piece in a room agrees on what worn steel looks like. Parts of a generated model come from PartCrafter [@lin2025partcrafter], and its picture only chooses which library surface each part takes; labels and notes go on as a few decals. Sound and light follow the same pattern of data and layers. Surfaces carry their footsteps and impacts, rooms their echo from their size and surfaces, and objects their own sound, generated by MOSS-SoundEffect [@moss2026] and chosen against its prompt by CLAP [@wu2022clap] (Appendix F); light is to be baked per lamp group as layers and mixed live by each lamp's brightness.

**The optional world step.** A concept shows one view, two or three walls and each object from one side. An optional world step turns it into a walkable whole-room reference from which every object and every wall can be seen; it served as the scene plan in early rooms of 2099 (World Labs Marble in our runs, credited "Generated using World Labs"), and its output is never shipped.

**Review tools.** The creator's review closes each place. SCORE supplies the tools for it: pages with each stage's outputs side by side, before and after shots from the same cameras, in-engine walkthroughs, and every check's result; how the creator judges with them is the creator's own.

::: gap
**Gap: Figure 2, the framework.** The stages with their kept outputs, the scene's base and edit layers, and the engine adapters. To be drawn with the scene export, which is being built in the framework repository.
:::

::: gap
**Gap: Figure 3, one place through the stages.** One place from concept to finished world, with each stage's output and the checks that fired on it. Waits on a place built and accepted on the final route.
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
**Gap: ablations.** The route with and without the optional world step, and with checks before spending switched off, on the same places: concept coverage, density of the built place, cost, faults after spending, and the creator's review. Waits on the route running from the framework repository.
:::

::: gap
**Gap: style coherence.** A measure of whether a place keeps one style, from rendered frames (colour distance to the palette per kind of source, lightness spread, ink density), validated against the creator's reviews. Designed, not built.
:::

::: gap
**Gap: robots in the simulation world.** A rigged robot loaded with the simulation world in a robotics simulator, with masses, friction and joints written into the scene, and motion from the framework's motion models. Waits on world 3.
:::

# Discussion and outlook

SCORE takes the opposite route to a world model. A world model learns to show only what the player sees, frame by frame; SCORE builds everything in detail, so that the world cannot break when the player looks somewhere unexpected and can be used today in existing engines. Neither route is right in general, and world models improve fast; what a built world keeps is that it can be edited, owned and loaded by an engine. Its cost is that everything must be built, which makes cheap content the easy part: as models make objects, surfaces and sounds cheap, the creator's direction becomes the scarce input, which is why SCORE moves the creator's decisions to the start of each place and turns what can be checked into checks that need no attention. Whether that saves the creator time overall is not established; with early-2025 tools, experienced developers on familiar code were slower with AI than without [@becker2025metr].

The route has clear weaknesses. Code builders are clean but need an agent to write one per kind of object, which scales worse than generation. A concept shows one side of a place, so built places come out sparser than their concepts; the concept-density check catches this but does not fix it, and the optional world step is meant to. Daily quotas on picture models, not compute cost, set the pace of a build.

Beyond the four worlds, SCORE is meant to be packaged so that a creator can run it through a coding assistant, and to reach further scales: worlds of galaxies or cells need open solvers wrapped as stages of their own, with orbital dynamics through REBOUND [@rein2012rebound] as the first.

<!-- Genie contrast and outlook: playtest3/paper-notes-owner.txt (2026-10-05, 2026-10-06). Attention thesis: 2099 paper README "Does the limit move?". Weaknesses: issue JoeyKardolus/2099#130 (lab, greenhouse, 2026-10-07/08); session record 2026-10-08T09:27Z; quotas #130 comment 2026-10-08T09:18. -->

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

# Development history

The route grew out of building the game 2099 between late September and early October 2026, one owner directing coding agents. Its first form joined four parts: rooms laid out in code, a scene plan from a world model painted on depth panoramas of those rooms, props from a picture-to-3D pipeline, and coding agents fitting each room to its plan. Eight places were fitted out to their plans in one day; the owner found them close to their plans in layout and mixed in style, with models from earlier rounds and objects the plans never showed. The cause was in the workflow: every pass added to a room and none checked what was placed against the plan. That gave the inventory as a hard list, nothing made or placed outside it, and the look decided before anything is spent. Structure then moved to concept cutaways drawn from the owner's own reference pictures (he picked one of twenty for the hub), and scale moved into a dimensioned plan drawn before the concept, after the first cutaway came out at doll-house scale (about 13 m across by its crew against the 8 to 9 m asked).

<!-- 2099 paper README (fifth pass): "The first rooms built to their plans", "The hub: from the owner's references to clay", 13 m vs 8 to 9 m; material/10-objects-and-building.md fourth and fifth passes. -->

## The hub in six rounds

The mechanisms of Section 2 then came out of six rounds on one room, the central hub of the game 2099, on 6 and 7 October 2026, each answering the creator's verdict on the last (Table C1). The first two rounds were decided by side-by-side comparison of the old and new route on the same cameras.

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

Every model must allow commercial use of its output (Table E1); candidates were dropped on this rule, among them NVIDIA's Lyra 2.0 (weights for internal research only) and Hunyuan3D 2.1 (its licence does not apply in the European Union). Licences were read for their commercial-use clauses. Four of these models read pictures through Meta's DINO family, each through its own copy; what passes between them is pictures, masks, depths and meshes, never one model's inner features.

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
| FLUX.2 klein 4B [@flux2klein] | earlier prop pictures | Apache-2.0 |
| MoGe-2 [@wang2025moge2], SAM 3 [@carion2025sam3] | measuring and finding objects in pictures | MIT; SAM Licence |
| Kimodo [@rempe2026kimodo], SAM 3D Body [@yang2026sam3dbody] | motion from sentences; body shape from a picture | Apache-2.0 code, NVIDIA Open Model License; SAM Licence |

Picture-to-3D, parts, surface bakes, sound, checks and assembly are automatic. Coding agents (Claude Code [@claudecode]) write the plans, inventories and every code builder; in the hub's final round 86 of its 98 models were code. Hand steps remained: some generated objects turned to face the right way by eye, a few labels placed by hand before a rule replaced that. Concepts and verdicts are the creator's picks.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. -->

# Surfaces, sound and light

The library holds families of variants (painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light and print; 71 variants from 14 ProcFunc recipes after the hub's second round), each a recipe with settings, coloured only from palette tokens and baked to base colour, metal-roughness and normal maps at a texel density by reach. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor a piece stands on. Every sound has a brief written from its object; four takes are generated, scored by CLAP against the prompt less measured faults (clipping, unsteady loops, bad joins), and levelled to one loudness per kind under a -3 dBTP true peak. A creator may swap any take; for the game 2099 all 61 sounds were generated as 244 takes in one batch for €1.61, and the creator kept recordings for three kinds (breathing, a sliding door, steps on steel).

<!-- 71/14: progress-robust-exp.txt round two. Kick wear 32 cm: 2099 docs/bible.md item 11. Sound: 2099 docs/bible.md item 12; 2099 paper writing/status.md, seventh pass. -->

Light adds up, so it is planned as layers: for each kind of module, the bounce light of each lamp group (and a few sun directions through windows) is baked in the cloud as a layer, and the layers are mixed live by each lamp's brightness; outdoor and moving light stays live. This is not built yet.

<!-- Light layers: memory project-sound-and-light-layers (owner, 2026-10-06). -->

# Cost and infrastructure

Every heavy step runs on rented machines deleted after each batch: NVIDIA L4 cards for picture-to-3D, parts and bakes, processor machines when cards are out of stock. The engine's tests, shots and frame-time bench also run on rented machines; a full test run took 542 s there against 596 s locally, and L4 frame times convert to the local RTX 5080 by a measured factor of 3.47. Pictures cost about $0.134 each at the resolution used. The binding limit in practice was the picture model's shared daily quota of 250 pictures, not compute.

<!-- 542 vs 596 s, 3.47: #130 comments 2026-10-07T21:57 and 23:02. $0.134: 2099 paper README "What it cost". 250 a day: #130 comment 2026-10-08T03:31. -->

::: gap
**Gap: cost tables.** Cost per batch kind and per world, reconciled with the cloud bill. Waits on the worlds; the per-place figures so far are floors from the build logs.
:::
