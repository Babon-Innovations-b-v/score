---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 9 October 2026"
abstract: |
  Games, films and robot training need 3D worlds that are complete, editable and owned by the people who make them. World models and one-shot 3D generators can produce a convincing place from a sentence or a picture, but they give frames that no engine can open, or one fused scene without separate objects or clear rights. Studios have always built worlds in stages, from concept art and layout to modelling, surfacing, sound and review. We present SCORE, a world generation framework that keeps these stages and automates large parts of them with open vision foundation models, procedural tools and coding agents, while the creator chooses and reviews. Because every stage's output is kept, the creator can rerun or fix any single stage, and because every model allows commercial use, the creator holds full commercial rights. We demonstrate SCORE on the game world of 2099 and plan three further worlds of different kinds. Open models, working in checkable stages, can build worlds that a creator owns and keeps editing. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT license).
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
**Gap: teaser figure.** This figure will show four worlds made with SCORE: the game world of 2099, a stylised underwater world, a simulation world for robots, and a third-person fantasy world. Each will appear as its chosen concept beside the finished world in its engine. It waits until the four worlds are finished and accepted by their creators.
:::

# Introduction

Interactive 3D worlds are the raw material of games, of film and of embodied AI, where agents are trained and tested in simulators [@yang2024holodeck]. Building such a world is still expensive. Every object has to be modelled, given surfaces, placed, given collision and physical properties, lit and given sound, all in one consistent style, and the world has to stay editable while the project changes. Generative models promise to take over much of this work, but the people who would use them are wary of it: in GDC's 2026 survey, 36 percent of game workers used generative AI at work, and 52 percent thought it was hurting the industry [@gdc2026survey]. Taking over the work is therefore not enough. A tool for building worlds has to keep the creator the author of the result, holding full commercial rights.

Two lines of research generate the world itself. The first, learned world models, generates it as frames. Genie learns an interactive environment from video [@bruce2024genie], and Genie 3 renders a world that a person can move through in real time; its announcement lists a constrained range of actions and a few minutes of continuous interaction among its limits [@genie3]. Nothing that these models produce can be opened in a game engine or an editor, and their world exists only as far as the player looks. The second line, 3D world generators, produces geometry instead. WorldGen turns a text prompt into a traversable scene for standard game engines [@wang2025worldgen], and HY-World 2.0 turns text or a picture into a single splat or mesh world [@hyworld2]. Most such outputs, however, are "static monolithic assets with limited editability and physical interaction" [@hu2026worldact], and WorldAct and WorldSculpt address this by recovering separate objects from them after the fact [@hu2026worldact; @niu2026worldsculpt]. In both lines the world is generated in one shot. When part of the result is wrong, the creator can regenerate the whole world or repair it by hand, but cannot see which step caused the fault, and cannot change that step alone.

A third line of work keeps the world explicit. Infinigen and Infinigen Indoors build every asset from procedural rules, with materials as generators of their own [@raistrick2023infinigen; @raistrick2024indoors]. This gives real geometry and full control, but only over the content that the rules describe. Holodeck has a language model write layout constraints, which a solver then satisfies with assets retrieved from a library [@yang2024holodeck]. SceneCraft, recursive code world models, WorldClaw and AutoUE let coding agents write scenes, or whole games, as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue]. LEGO-Anything shows what such agents need. When coding agents rebuild a scene from a single picture, they start weakly, undo their own progress while editing, and judge their own geometry unreliably; giving them grounded tools, rather than training them further, closes much of that gap [@li2026lego]. All of these systems, however, either rebuild a scene that already exists or draw their objects from a fixed library of assets.

Meanwhile, each of the parts that a world needs can now be read out of pictures by an open model. Vision foundation models learned the world from images in the way that language models learned it from text [@oquab2023dinov2]. They can now turn a picture into a 3D shape aligned with its pixels [@li2026pixal3d], into a mask for each named object [@carion2025sam3], into depth in metres [@wang2025moge2; @yang2024dav2], into the parts of an object [@lin2025partcrafter] or into a human body [@yang2026sam3dbody]; related models turn a sentence into motion [@rempe2026kimodo] or into sound [@moss2026]. Most of these models pass on pictures, masks, depth maps or meshes rather than their internal features, so a coding agent can connect them to one another as it would connect tools. What none of them provides is one consistent style across objects that different models have made. The field names this as an open problem [@wu2026production; @yang2026flowscene], and Hunyuan3D Studio addresses it only by restyling the input picture [@lei2025hunyuanstudio].

Studios have always built worlds in stages: concept art, layout, asset lists, modelling, surfacing, sound and review. Each stage has a clear output that a person can check before the next one starts, which makes this way of working the natural basis for a world generation framework. SCORE keeps these stages and automates large parts of them with the models above, with procedural tools and with coding agents, while the creator chooses and reviews. Its name states what it aims for. The worlds it makes are **complete**: every object, surface, light and sound exists wherever the player looks. They are **owned**: the creator decides what the world is, edits it in the tools they already use, and stays its author, holding full commercial rights, because every model in the framework allows commercial use of its output. They are **responsive**: the world answers to the physics engine that loads it, because every object has real collision, mass and material, so it behaves physically in any engine or simulator, under physics that each world may set for itself, such as the low gravity of the Moon. And they can be any kind of **environment**, real or made up. SCORE does not compete with procedural tools, part splitters or world generators; it takes them in as building blocks wherever their licences allow. It also does not generate a world in one shot: the creator chooses the look, the concept and the style of each place, and coding agents and models do the work of the stages between those choices. To our knowledge, no other openly available world generation work joins vision foundation models into engine-ready scenes that are built from reference pictures, steered by a person's choices at each step, and made only with models that allow commercial use of their output.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Hand-off pattern: material/11-vision-foundation-models.md. -->

This paper makes three contributions:

- **The SCORE framework:** staged, retraceable generation from a creator's choices to one canonical scene, which consists of a generated base layer and the creator's own edit layers (Section 2).
- **The mechanisms that keep its worlds coherent and make faults cheap to fix:** deterministic checks before every stage that costs money, a parts check that decides how each object is built so that every real-world object becomes one model, a shared library of rule-based surfaces that keeps shape and surface apart, and review tools for the creator (Section 2).
- **Evidence from four worlds of different kinds:** the time, the cost and the faults caught before spending at every stage, and an evaluation on a shared benchmark (Sections 3 and 4).

# Methods

![The stages on one place, the central hub of the game 2099. (a) The concept, drawn by a picture model from the creator's reference pictures and chosen by the creator. (b) The dimensioned plan in metres, with walkways and standing spots. (c) An excerpt of the scene inventory, which has 74 rows. (d) Close-up pictures of two objects. (e) One surface from the shared library of rule-based surfaces at three wear settings. (f) The assembled room in the game engine.](figures/fig-overview.jpg){width=100%}

Figure 1 shows the stages on one place. The creator chooses a concept (a), and a coding agent turns it into a dimensioned plan (b) and a scene inventory (c). An open picture model draws a close-up of every object in the inventory, and a closed one redraws those that fail a shape check (d). Each object is then built in code or generated in 3D, its parts are painted from the shared library of rule-based surfaces (e), and the place is assembled in an engine (f). The output of every stage is kept, so the creator can trace a weak result to the stage that caused it, rerun or fix that stage, and regenerate the stages after it while keeping their own edits. The sections below describe each stage with an example.

<!-- Hub concept C12, plan v3, inventory data/inventory/hub.json (74 rows), close-ups hubrefs/c12/clean, swatches robust-exp/img, shot robust-exp/r6/shots/now/wide-south. -->

## Inventory as a partition of the concept

![The inventory of the lab on the Moon base, built from its concept. Left: the concept, cut into twelve tiles. Right: examples of how each visible element maps to an inventory row, or is dropped with a written reason. Of the 47 elements in this concept, 40 were mapped to inventory rows and 7 were dropped with a written reason.](figures/fig-partition.jpg){width=100%}

The inventory decides what exists in a place. A coding agent cuts the concept into tiles and lists every visible element, and each element either becomes a row (with its kind, anchor, size and count) or is dropped with a written reason (Figure 2). Nothing is made or placed that is not a row. After the build, the place is rendered from the concept's own camera and compared with the concept; a place that is clearly sparser than its concept fails this concept-density check.

<!-- place-lab/tools/elements.json: 47 elements, 7 dropped. Rule: memory project-scene-workflow (2026-10-08); issue #130, 2026-10-07T23:04. -->

## Close-ups: the open model first

Every object is built from a close-up: a picture of the object alone on a plain background, drawn from its crop of the concept. Qwen-Image-Edit-2511 [@qwenimageedit], an open model that runs on our own rented cards, draws every close-up first. A shape check then decides, without a person, whether the picture may go on to the 3D step. Its first half measures the picture: a plain border all round, one object filling a sensible share of the frame, and an outline in the proportions of the inventory row's box. Its second half is an open vision-language model, Qwen3.8-27B [@qwen38], which sees the crop beside the close-up and answers set questions (one object, a clean background, the whole object, the same object, no parts missing or added, the right proportions); each question is asked three times with different seeds and the majority decides. Only a close-up that fails is redrawn by Nano Banana Pro [@nanobananapro], first from the crop alone and then with the whole concept beside it, and its pictures pass the same check. The check leans towards failing, because a wrong picture that passes costs a bad 3D model, while a good one that fails costs only a picture from the closed model (Appendix E).

<!-- Stage and check: tools/props/closeup/stage.py and check.py (score d323674, 87e5ffb); the owner's decision of 2026-10-08 (briefs/score-common.txt, CLOSE-UPS). -->

## Code or generation: the parts check

![The parts check decides how each object is built. Top: the close-up picture of four objects. Bottom: the object as built. The notice board and the tall locker are built in code, because their code builds show every part of their close-ups. The microscope and the desk chair are generated with Pixal3D, because no code build shows all of their parts.](figures/fig-parts-check.jpg){width=100%}

Picture-to-3D models build chunky solids well, but flat panels, thin beams and openings badly, while code builders are exact and straight but show only the parts that the coding agent wrote. For each kind of object, the parts check renders a code build from the front and compares it with the close-up picture: if every part of the close-up is visible in the build, the kind is built in code, and otherwise it is generated from the close-up with Pixal3D [@li2026pixal3d] and made solid (Figure 3). Composite objects are split in the inventory, so that every real-world object becomes one model: a console, for example, becomes a desk carrying separate monitors and keyboards.

## Shape and surface apart

![(a) Three surfaces from the shared library of rule-based surfaces (painted panel, bare steel and deck plate) at wear settings 0, 0.4 and 0.8. (b) The hub's tool board when each generated piece kept the colours of its own picture (left), and after every surface came from the library and each tool became its own model (right). Both shots use the same camera and the same build of the game.](figures/fig-surfaces.jpg){width=100%}

Models and code builders give shape only. Every part of every object takes one surface from a shared library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] that are built on Infinigen's shaders [@raistrick2023infinigen] and take their colours from the place's palette (Figure 4a). A room has one wear setting, and wear is applied where it has a cause, such as edges and the places where feet pass. On a generated model, PartCrafter [@lin2025partcrafter] splits the shape into parts, and an open vision-language model, shown each part outlined on the close-up, names the library surface it takes; the picture's colours are not kept. Figure 4b shows why: when each piece kept the colours of its own picture, every piece brought its own rust and stains, and the room looked inconsistent. Sound is attached in the same way, to surfaces, rooms and objects, and is generated by MOSS-SoundEffect [@moss2026] (Appendix F).

## Terrain

![The stages for large outdoor places, on the ground around the Moon base. (a) The dimensioned plan with the base's flat areas and paths. (b) A diorama picture drawn over the plan. (c) The heights that follow the diorama, shown shaded. (d) The skin painted over the plan. (e) The result in the engine, seen from a crater rim.](figures/fig-terrain.jpg){width=100%}

Large outdoor places follow the same pattern (Figure 5). A dimensioned plan places the flat areas and paths the place needs (a), a diorama picture drawn over the plan sets the landforms (b), and the heights follow the picture (c). A skin is painted over the plan, with fine relief from monocular depth [@yang2024dav2] (d), rocks are single generated models, and everything is built on the world's own curved ground (e).

## Checks before spending

![A fault caught by the placement check. (a) In the first build of the hub, a conduit box covered the porthole. (b) In the current framework, the placement check found the box in front of the opening and moved it 0.5 m along the wall before anything was spent.](figures/fig-checks.jpg){width=100%}

Deterministic checks run before every stage that costs money. They test real geometry rather than relying on an agent's judgement, because a fault costs nothing to fix in the plan but an evening of the creator's time once the place is built. The checks look for light leaking out of the room, pieces in front of openings or off their surface, doors that do not separate their two sides, models that are open, too thin or leaning, and surfaces off the palette (Appendix D). Figure 6 shows one fault the placement check caught. A failed check sends the work back one stage.

<!-- Porthole: robust-exp progress log [gates] ("Placement gate slid the conduit box 0.50 m along its wall"); shots robust-exp/img x/y-porthole-close (x = A, y = B for round one). -->

## The canonical scene

Every place is exported as one OpenUSD stage [@openusd] in which each object carries its kind, its transform in metres, its collision, the library surface of each part and that surface's sounds, with the generated base layer under an edit layer that belongs to the creator, so that an edit survives when the base is generated again (Figure 7).

![The wreck, one outdoor place of the game 2099, as an OpenUSD stage. (a) The place in the game, from one of its fixed cameras. (b) The stage loaded in Blender and rendered from the same camera. (c) Blender's object outlines drawn over the game's picture. (d) The same camera after an edit in the edit layer, made here by a script, that moved the round cover and gave the capsule's painted hull another library surface, and after the base layer was generated again.](figures/fig-usd.jpg){width=100%}

<!-- Wreck stage: tools/usd/export.py on data/kit/wreck.json; renders by tools/usd/views.py (Blender 5.0.1, headless); the edit survival is checked by tools/usd/export_test.py. -->

A place's stage holds more than its inventory's objects. A scene record adds what the place needs around them, each piece built by a code builder and painted from the library: the room's shell and stairs, the ground out to the horizon, water, the far backdrop, the neighbouring places seen through open doorways (each referenced as its own stage), every light with the sky and the exposure, and the cameras that the place is judged from.

<!-- Scene record: tools/usd/scene.py, builders.py, data/scene/<place>.json (score f51d92b, 2708ff2, 3a28fe7); 17 records for world 1 (data/scene). -->

Before a place is accepted, its loose objects are dropped in a physics simulation on the stage's own ground with their own triangles, and each rest pose is written back into the layout. Settling only corrects: an object that would turn or drift further than a small limit keeps its laid pose and fails the resting check, which also fails anything floating, tipping, sunk into the ground or lying inside another piece (Appendix D). A large move is a fault of the layout, not of physics, and the layout follows the creator's concept. On the wreck, 11 of 22 pieces rested as first laid. The coordinating agent then laid the wreck out again after its concept and cut shallow dents in the ground where pieces had struck it, and all 22 rested; the creator has not yet reviewed this new layout. On the old station, the check found a pile of sandbags lying inside the lander's legs, and once the pile was moved, all 29 pieces rested.

<!-- Settling and the resting check: tools/usd/settle.py, resting.py, ground.py dent (score e5d829c); wreck 11/22 before and 22/22 after, old station 29/29 with bag_pile_5 moved: progress-usd.txt 2026-10-08T23:27. -->

A place's people are part of its stage. Its cast records who is there, how many, where, doing what and why each is there, and nobody is placed who is not in it. Each person becomes a skinned character (UsdSkel) that plays a clip from its own starting point, in a layer of its own between the creator's edit layer and the base. A crowd is one point instancer of a cheap body, with a prototype for each clip, phase and palette of clothes. The bodies come from the game 2099's character tools: SOMA-X bodies shaped by SAM 3D Body [@yang2026sam3dbody], clips that Kimodo wrote from sentences [@rempe2026kimodo], and clothes draped by GarmentCode. On the leader's walk, UsdSkel skins the converted body to within about a micrometre of the points the glTF file's own skinning gives. The prologue's square holds the leader on the podium, a front row of 24 people mixed from six kit builds, and a crowd of 10,000.

<!-- Characters: tools/characters (skel_usd.py, cast.py), data/characters/square.json; skinning agreement measured 2026-10-08 on the leader's walking clip, frame 20 (max 0.0013 mm); checked by tools/characters/characters_test.py. -->

::: gap
**Gap: the scene in a game engine.** The same stage loaded in a game engine, with its collision and surfaces, and the mass and friction of each object written into it. It waits on the game engine adapter and on the framework recording mass and friction.
:::

## Review tools

Each place ends with the creator's review. The review tools that SCORE supplies are pages that show each stage's output side by side, before-and-after shots from the same cameras, walkthroughs inside the engine, and the result of every check. An optional world step can turn the concept into a whole room that can be walked through, so that walls and objects the concept does not show can be seen; nothing it produces is shipped.

A review page is a static folder built only from the files the stages wrote, with the assembled scene rendered by Blender from the place's OpenUSD stage, on rented cards, from the cameras of its scene record and along a walk through it (Figure 8). Each view is laid beside the game's own shot from the same spot, and a view that is much darker than the game's fails a brightness check, which is how lamps whose light fell off too fast were found. A place with people shows each of them close and the crowd wide, and its walk is drawn at consecutive moments of the stage's time, so that the people move.

![The wreck's review page, from two runs of the route over the same place. (a) One model: its close-up, its labelled parts (one colour per library surface) and its baked model, each from the first run and the rerun, drawn from the same camera. (b) The assembled scene from one fixed camera, before and after the rerun. (c) The parts check for each take, with what it caught in the rerun: the split of seven takes did not register against their pictures, so each was painted whole.](figures/fig-review.jpg){width=100%}

<!-- Scene record views, game shots, brightness: tools/review/CLAUDE.md, page.py --game-shots (score f51d92b); the lamps: score 3a28fe7 (the rocket's floodlight, progress-complete-scenes.txt 00:00). Characters section: tools/review/characters.py (score 93df6a5). Page: tools/review/page.py wreck, runs place-outside/work/wreck (before) and ~/.farm-factory-props/work/place/wreck-score1 (now); "seven takes": the labels.json files in wreck-score1/parts, registration.registered false in 7 of them. -->

# Results across worlds

We build four worlds with the same stages: the game world of 2099 (a Moon base and its surroundings, a camp on Mars, and a prologue on Earth), a stylised underwater world, a simulation world for robots, and a third-person fantasy world.

::: gap
**Gap: Table 1, results per world and stage.** For each world, this table will give the number of places, the wall-clock time, the cost in GPU time and in picture calls, the number of models built in code and generated, and the faults caught before spending at each stage against those found afterwards. All 17 places of world 1 are built and their records are in Appendix B, but they become results only when the creator has reviewed the world, which has not happened since its first room; worlds 2 to 4 have not been started.
:::

::: gap
**Gap: figure of one place per world.** This figure will show one representative place from each world beside its concept, rendered from the concept's own camera. It waits on the same worlds; every place will be shown in Appendix A.
:::

# Evaluation

::: gap
**Gap: LEGO-Bench.** This section will report SCORE's scores on LEGO-Bench [@li2026lego], a benchmark of scenes rebuilt from pictures. It waits until the benchmark's code is released and until SCORE's scene export and its Blender adapter are built.
:::

::: gap
**Gap: ablations.** This section will compare the framework with and without the optional world step, and with the checks before spending switched off, on the same places. It will measure how much of the concept is covered, how dense the built place is, the cost, the faults found after spending, and the creator's review. It waits until every stage runs from the framework repository.
:::

::: gap
**Gap: style coherence.** This section will measure whether a place keeps one style, using rendered frames: the colour distance to the palette for each kind of source, the spread of lightness, and the density of ink lines, validated against the creator's reviews. The measure is designed but not yet built.
:::

::: gap
**Gap: robots in the simulation world.** This section will show a rigged robot loaded together with the simulation world in a robotics simulator, with masses, friction and joints written into the scene, and with motion from the framework's motion models. It waits on world 3.
:::

# Limitations

- **One creator, one world so far.** Every verdict on the results is one creator's, and only the first world has been built.
- **Code builders do not scale well.** They give clean objects, but a coding agent has to write one for every kind of object.
- **Places come out sparser than their concepts.** The concept-density check catches this but does not fix it.
- **One stage still depends on a closed, paid picture model.** Nano Banana Pro, a closed and paid service, draws the concepts and every close-up that the open model's pictures fail. On the last 17 close-ups of world 1, none of the open model's pictures passed the shape check, so the closed model drew every close-up that was accepted. Its daily limits set the pace of world 1, and it can change or be retired, which limits reproducibility and leaves a public framework depending on a closed service for one stage. A cheaper model of the same family did not replace it (Appendix E).
- **Parts do not follow finishes.** PartCrafter's parts follow shape, not paint, so a finish that does not have its own part, such as a gold foil patch on a white hull or a brown seat on a grey frame, is still lost when the part is painted with one surface.
- **Objects are physical but not interactive.** Seats, terminals and other usable objects do not work in the output.


# Future work

- Build the three further worlds: a stylised underwater world, a simulation world for robots, and a third-person fantasy world.
- Add a game engine adapter for the OpenUSD scene, and write each object's mass and friction into it.
- Make assets interactable, which robotics in particular needs.
- Make the other worlds' animals the way people are made, from a picture of each to a rigged, animated character, starting with fish for the underwater world.
- Make the open picture model's close-ups pass the shape check more often, so that the closed model is needed less.
- Wrap open solvers as stages for worlds at other scales, starting with orbital dynamics through REBOUND [@rein2012rebound].
- Evaluate SCORE on LEGO-Bench [@li2026lego].

# Conclusion

SCORE builds complete, owned and responsive worlds from a creator's choices, by joining open vision foundation models, procedural tools and coding agents into fixed stages whose outputs are kept. On its first world, the parts check, one model per real-world object and the shared library of rule-based surfaces made a room consistent, and the deterministic checks before every stage that costs money caught faults before money was spent. Whether the framework holds across different kinds of worlds is what the remaining worlds and the benchmark will show.

# References {-}

::: {#refs}
:::

# Appendix {-}

```{=latex}
\appendix
```

# Per-world demos

::: gap
**Gap.** This appendix will show every place of every world as its concept beside the finished build, with links to demo videos and playable builds. It waits until the worlds are finished.
:::

# Detailed per-stage results

Table B1 gives the records of world 1's 17 places as the build logs and the cloud ledger hold them. They are records, not yet results: the creator has not reviewed world 1 since its first room, and worlds 2 to 4 have not been started. The cloud costs are lower bounds. The ledger attributes a batch to a place by the work folders and take names in it; review renders (€24.24), the shape-check judge (€22.81), the game's shared test machines (€32.63), settling (€4.43), the open picture models (€10.27) and the repainting and spreading work (€8.44) could not be attributed to one place. No time or cost is recorded for each stage of a place separately, only for each batch, so the table gives none. The resting check is the one on each place's review page of 8 October, before the night's complete stages were exported; it counts every piece it fails, including many deck plates that it finds sunk by 4 cm, which have not been judged as real faults or not.

**Table B1.** World 1, per place. Models are those built in code and those generated. Cloud is the ledger's rented machine time attributed to the place, in euros; pictures are the picture model's calls in dollars, from the build logs. Faults are those the checks caught before money was spent and those found after.

| Place | Rows | Pieces | Models, code / generated | Cloud | Pictures | Faults before / after | Resting |
|---|---|---|---|---|---|---|---|
| Hub | 74 | 460 | 88 / 12 | €3.65 | $1.07 | not counted | 405 of 460 |
| Lab | 47 | 412 | 54 / 22 | €8.36 | $4.15 | 13 / 12 | 373 of 412 |
| Greenhouse | 59 | 1,248 | 146 / 3 | €3.07 | $2.13 | 7 / 3 | 1,154 of 1,248 |
| Workshop | 54 | 814 | 97 / 8 | €2.18 | $3.35 | 3 / 9 | 671 of 814 |
| Airlock | 33 | 330 | 73 / 1 | €2.53 | $0.13 | 1 / 5 | 296 of 330 |
| Walkway tube | 13 | 39 | 23 / 0 | €0.81 | $0 | 0 / 2 | 38 of 39 |
| Habitat | 53 | 637 | 100 / 2 | €5.70 | $1.34 | 1 / 4 | 543 of 637 |
| Garage | 41 | 602 | 75 / 19 | €4.29 | $8.71 with the hangar | 3 / not counted, with the hangar | 493 of 602 |
| Hangar | 37 | 1,686 | 61 / 13 | €4.22 | with the garage | with the garage | 865 of 1,686 |
| Wreck | 14 | 22 | 3 / 13 | €4.88 | $2.68 | 2 / 1 | 22 of 22 |
| Old station | 17 | 28 | 10 / 14 | €4.93 | $3.22 | 5 / 2 | 29 of 29 |
| Mars camp | 33 | 218 | 51 / 5 | €3.47 | $1.21 | 4 / 8 | 127 of 218 |
| Launch view | 4 | 67 | 4 / 1 | €0.33 | $0.40 | 1 / 2 | 8 of 67 |
| Square | 40 | 4,135 | 74 / 2 | €1.64 | $1.07 | 3 / 4 | 3,712 of 4,135 |
| Street | 33 | 1,198 | 45 / 2 | €0.98 | $1.74 | 7 / 6 | 1,179 of 1,198 |
| Stairwell | 21 | 118 | 42 / 1 | €1.23 | $2.41 with the flat | 2 / 6 | 117 of 118 |
| Flat | 38 | 52 | 35 / 9 | €2.44 | with the stairwell | 5 / 6 | 50 of 52 |
| World 1 | 611 | 12,066 | 981 / 127 | €54.71 | | | 10,082 of 12,066 |

<!-- Rows: data/inventory/<place>.json (flat and stairwell: prologue_flat.json, prologue_stairwell.json). Pieces and models: data/kit/<place>.json (pieces; models[*].route code or model), glow parts left out. Cloud: ~/.farm-factory-props/cloud/ledger.jsonl rows from 2026-10-07T00:00Z, attributed by work folder and take name (bakes split per job entry, Pixal3D by job seconds, PartCrafter by folder; the hub's round six only, rows 219-236 and 239); unattributed sums the same way. Pictures and faults: playtest3/scaling-world1.tsv columns gemini_usd, faults_caught_before_spend, faults_after (lab rows 6 and 21 added: $2.68 + $1.47, faults 9/9 + 4/3); hub pictures progress-hub-r5.txt; the hub's faults are not tabulated in the tsv. Resting: "Resting on the ground" tables of ~/.farm-factory-props/work/review/<place>/index.html, 2026-10-08 17:05 to 23:25; wreck and old station progress-usd.txt 23:27. The world's resting total over 12,066 pieces: the per-place counts summed (the old station's 29 objects include a child piece). -->

# Development history

The framework grew out of building the game 2099 between late September and early October 2026, with one owner directing coding agents. In its first form it joined four parts: rooms laid out in code, a scene plan from a world model that painted depth panoramas of those rooms, props from a picture-to-3D pipeline, and coding agents that fitted each room to its plan. Eight places were fitted out to their plans in a single day. The owner found that their layouts were close to the plans, but that their styles were mixed, with models from earlier rounds and with objects that the plans never showed. The cause lay in the workflow: every pass added things to a room, and no pass checked what had been placed against the plan. This led to the inventory as a strict list, with nothing made or placed outside it, and to deciding the look before any money is spent. The structure of each room then came from concept cutaways drawn from the owner's own reference pictures; for the hub he picked one cutaway out of twenty. Scale moved into a dimensioned plan drawn before the concept, after the first cutaway came out at doll's-house scale: about 13 m across, judged by the people drawn in it, against the 8 to 9 m that had been asked for.

<!-- 2099 paper README (fifth pass): "The first rooms built to their plans", "The hub: from the owner's references to clay", 13 m vs 8 to 9 m; material/10-objects-and-building.md fourth and fifth passes. -->

## The hub in six rounds

The mechanisms of Section 2 then came out of six rounds of work on one room, the central hub of the game 2099, on 6 and 7 October 2026. Each round answered the creator's verdict on the round before (Table C1). In the first two rounds, the creator chose between the old and the new method by comparing them side by side from the same cameras.

**Table C1.** The hub's six rounds. Cost is given as rented GPU time in euros and picture-model calls in dollars. Frame time is the mean frame time on an RTX 5080, in the night scene, at 1600×900.

| Round | Change | Creator's verdict | Cost | Frame time |
|---|---|---|---|---|
| 1, two walls, A/B | surface library, routing by shape, room checks | chose the new method ("Y looks much cleaner") | €0.88 | 7.81 ms vs 7.53 |
| 2, two walls, A/B | 71-variant library, shared texture sets, roof check | chose the new method again | €1.70 | 8.05 ms vs 8.24 |
| 3, whole room | all stages end to end, 74 models | old models were still loaded; labels and floor fittings were wrong | €1.67 | 6.78 ms (old 9.22) |
| 4, whole room | detail through the pipeline, picture colours kept | "pretty much all of this became messy" | €8.50, $5.09 | 9.6 ms |
| 5, eight pieces, A/B | shape only from the pipeline, library surfaces, parts check | new method preferred for the door, notice board and porthole; three pieces still wrong | €0.21 | not run |
| 6, whole room | round 5 everywhere, one model per object, straightness check | "this looks amazing, I have no negative feedback" | €3.48, $1.07 | 5.6 ms |

<!-- R1: local R&D log progress-robust-exp.txt [A/B numbers], blind key, quote at "ROUND TWO". R2: [A/B round two], [spend round two]; session record 2026-10-06T16:52Z. R3: progress-robust-exp.txt round three and fix round. R4: progress-hub-r4.txt; #130 comment 2026-10-07T05:29; quote in brief job-hub-r5-test.txt. R5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt. R6: progress-hub-r5.txt ROUND SIX; #130 comments 2026-10-07T15:55 and 16:20. -->

Three findings shaped the method. First, deterministic checks catch what agents miss. In round one, the share of rays that leaked out through walls and roof fell from 1.53 percent of 5,817 rays to zero, and the colour noise within surfaces fell from a median of 31.1 to 3.2 percent. Only walking through the loaded room, however, showed that 26 old models were still in it, and that finding became the made-only check. Second, when each generated piece kept the colours of its own picture, every piece brought its own wear, and the room looked inconsistent; surfaces have since come only from the library. Third, generated composite objects melted their parts together, and generated boxes leaned (one locker by 13 degrees). This led to one model per real-world object and to the straightness check (Figure 4b). By round six the room used 0.45 million triangles, against 1.96 million in round four, and 187 MB on disk, against 487 MB.

<!-- Numbers: progress-robust-exp.txt [A/B numbers] and round three fix round; 2099 docs/bible.md item 11 (locker); #130 comment 2026-10-07T15:55 (round six vs four). -->


# Check details

- **Room checks** take about two seconds per room and run on the laid-out meshes. They cast rays to find light leaking out through walls and roof, find pieces placed in front of a real opening, find roof and wall fittings more than 3 cm off their surface or turned more than 5 degrees from it, and count pieces, triangles and lamps against the room's budget.
- **Door check:** every door must stand in a wall or partition that fully separates its two sides. The check tests this by walking a grid from one side to the other.
- **Concept-density check:** the concept picture is cut into crops, and every visible element must have an inventory row or a written reason for leaving it out. After the build, the place is rendered from the concept's camera and shown beside the concept.
- **Parts check:** in the code build, every part shown in the close-up picture must be at least 10 percent visible from the front, and no label may cover a part.
- **Model check:** every model must be a closed solid with walls at least 3 mm thick. A generated box fails if one of its sides tilts more than 2 degrees or is warped. The step that makes a generated model solid stops itself if the model's bounding box grows more than 3 percent.
- **Palette sweep and storage budget:** the colours of every model are compared with the place's library palette, and each room may use at most 250 MB on disk and 640 MB of textures on the graphics card.
- **Scene check and made-only check:** in the engine, these checks find anything that floats, sinks or overlaps, and any visible mesh that the framework did not make. A made-only finding can never be waived.
- **Close-up shape check:** the picture must have a plain border all round, one object filling a sensible share of the frame, and an outline within a set proportion of the inventory row's box; the judge's seven questions must pass by a majority of three sampled answers. A close-up passes only when both halves pass.
- **Settling and resting check:** on the OpenUSD stage, loose objects are dropped with their own triangles onto the ground and the fixed objects. An object that would turn more than 15 degrees or drift more than 30 cm keeps its laid pose and is marked as not resting; small debris, with no side over 1.4 m, may turn freely and drift up to 1 m. The resting check then fails anything floating, tipping, sunk below its contact points, lying inside another piece or marked as not resting. Hung objects are exempt by their inventory anchor, and fixed objects are not judged for tipping.
- **Brightness check:** each view of a place's stage on its review page is shown beside the game's shot from the same spot, and a view whose mean brightness is under half the game's fails.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). Close-up check: tools/props/closeup/check.py. Settling and resting: tools/usd/CLAUDE.md, settle.py, resting.py (15 degrees, 30 cm; debris 1.4 m, 1 m). Brightness: tools/review/CLAUDE.md (a scene view under half the game's). -->

# Models and licences

Every model in the framework must allow commercial use of its output (Table E1). Candidate models were dropped under this rule; among them were NVIDIA's Lyra 2.0, whose weights are licensed for internal research only, and Hunyuan3D 2.1, whose licence does not apply in the European Union. We read each licence for its clauses on commercial use. Four of the models read pictures through Meta's DINO family of models, each through its own copy. What passes from one model to the next is always pictures, masks, depth maps or meshes, never one model's internal features.

**Table E1.** Models in the framework.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups the open model fails, ground skins | paid API |
| Qwen-Image-Edit-2511 [@qwenimageedit] | close-ups, first | Apache-2.0 |
| Qwen3.8-27B [@qwen38] | the close-ups' shape check; each part's material | Apache-2.0 |
| Pixal3D [@li2026pixal3d] | picture to 3D | MIT; DINOv3 licence [@simeoni2025dinov3] for its encoder |
| PartCrafter [@lin2025partcrafter] | parts | MIT; its non-commercial background remover not used |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surfaces | BSD-3-Clause |
| MOSS-SoundEffect v2.0, CLAP | sound | Apache-2.0 |
| World Labs Marble [@marble_terms] | optional world step | paid; outputs owned by paid users |
| FLUX.2 klein 4B [@flux2klein] | earlier prop pictures | Apache-2.0 |
| MoGe-2 [@wang2025moge2], SAM 3 [@carion2025sam3] | measuring and finding objects in pictures | MIT; SAM Licence |
| Kimodo [@rempe2026kimodo], SAM 3D Body [@yang2026sam3dbody] | motion from sentences; body shape from a picture | Apache-2.0 code, NVIDIA Open Model License; SAM Licence |
| SOMA-X and MHR, GarmentCode with its Warp fork, MakeHuman eyes | the characters' bodies, clothes and eyes | Apache-2.0; MIT; CC0 |

On our tier, Nano Banana Pro allows 250 pictures a day and 20 a minute; the cheaper Nano Banana (gemini-2.5-flash-image) allows 2,000 a day and 500 a minute. We tested whether the cheaper model could draw the close-ups instead, on the same 10 lab objects with the same prompts and inputs (Table E2). It refused the standard prompt for 6 of the 10 objects and drew those only from the crop alone, and its pictures were about one megapixel with the object small in the frame. Close-ups therefore stay on Nano Banana Pro.

**Table E2.** Ten lab close-ups drawn by Nano Banana instead of Nano Banana Pro.

| Result | Objects |
|---|---|
| good | 2 |
| usable | 3 |
| marginal | 1 |
| wrong shape (microscope, chair, sample tray) | 3 |
| refused (glovebox) | 1 |

<!-- Tier limits and the 10-pair check: /home/dupe/.claude/jobs/3326150f/tmp/briefs/score-common.txt, lines PICTURE MODELS and CLOSE-UP CHECK RESULT (2026-10-08); check page https://claude.ai/artifact/J3cbncinKkyPJuNhwk47uH (private). -->

The close-ups' shape check was tuned on 40 close-ups that four open picture models drew of the lab's ten objects, each scored by hand as good, usable, marginal, wrong or failed, and on Nano Banana Pro's ten pictures of the same objects. With the majority of three sampled answers, the check agreed with the hand score on 29 of the 40, passed all ten of the closed model's pictures and two marginal ones, passed none of the pictures scored wrong or failed, and failed nine that were good or usable, each of which then cost a picture from the closed model. The judge's single answer at temperature zero was rejected: asked the same 51 questions twice in one batch, it gave a different verdict on 7 of them. On the lab's 22 generated rows, an earlier version of the check accepted 8 of the open model's close-ups and sent 14 to the closed model; 7 of the closed model's first pictures failed for drawing the room or dimension lines around the object, and all 7 passed when redrawn from the crop alone. On the 17 rows that world 1 still needed afterwards, from three places, none of the open model's pictures passed; the closed model's pictures were accepted for 10 rows, and 7 rows were left for the creator to look at.

**Table E3.** The close-up stage on world 1. Cloud is rented card time in euros; the closed model's pictures are in dollars.

| Run | Close-ups | Open model accepted | Closed model accepted | Left for the creator | Cloud | Closed model |
|---|---|---|---|---|---|---|
| Lab, 22 rows (earlier check: one answer) | 22 | 8 | 14 | 0 | €4.12 | $2.81 |
| World 1's remaining rows (three places) | 17 | 0 | 10 | 7 | €3.06 | $4.02 |

<!-- Tuning: progress-openpics.txt 18:53 (vote: 29/40 agree, 0 wrong/failed passed, 2 marginal passed, 9 wrong fails; Pro 10/10), greedy rejected 17:56 (7/51 differed). Lab: progress-openpics.txt 17:35 (8 Qwen, 14 Pro, 7 Pro first takes failed for the room or dimension lines, all crop-only retakes passed, EUR 4.12 cloud, $2.81 Pro). World 1: progress-world1-score.txt 18:55 (workshop, greenhouse, campgrounds; 17 rows) and 20:12 (10/17 accepted, all by Pro, Qwen 0/17, 7 for review, EUR 3.06, Pro $4.02). -->

The picture-to-3D step, the part splitting, the surface bakes, the sound generation, all checks and the assembly run automatically. Coding agents (Claude Code [@claudecode]) write the plans, the inventories and every code builder; in the hub's final round, 86 of its 98 models were built in code. Some steps were still done by hand: some generated objects were turned to face the right way by eye, and a few labels were placed by hand before a rule took over that job. The concepts and the verdicts are the creator's own choices.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. -->

# Surfaces, sound and light

The surface library holds families of variants: painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light and print. After the hub's second round it held 71 variants made from 14 ProcFunc recipes. Each variant is a recipe with settings, takes its colours only from the palette, and is baked into base-colour, metal-roughness and normal maps at a texture density that depends on how close the player can get. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor that a piece stands on. Every sound starts from a short written brief about its object. Four takes are generated for each sound, scored by how well CLAP matches them to their prompt minus any measured faults (clipping, unsteady loops or bad joins), and levelled to one loudness per kind of sound under a true peak of -3 dBTP. A creator may swap any take. For the game 2099, all 61 sounds were generated as 244 takes in one batch for €1.61, and the creator chose to keep earlier recordings for three kinds of sound: breathing, a sliding door, and footsteps on steel.

<!-- 71/14: progress-robust-exp.txt round two. Kick wear 32 cm: 2099 docs/bible.md item 11. Sound: 2099 docs/bible.md item 12; 2099 paper writing/status.md, seventh pass. -->

Light adds up, so it is planned as layers. For each kind of module, the bounce light of each group of lamps, and of a few sun directions through the windows, will be baked on rented machines as a separate layer, and the engine will mix these layers live according to each lamp's brightness. Outdoor light and the light on moving objects stay live. This part is not built yet.

<!-- Light layers: memory project-sound-and-light-layers (owner, 2026-10-06). -->

# Cost and infrastructure

Every heavy step runs on rented machines that are deleted after each batch: NVIDIA graphics cards for picture-to-3D, part splitting and baking, and processor-only machines when no cards are in stock. The engine's tests, its screenshots and its frame-time benchmark also run on rented machines. A full test run took 542 s there, against 596 s on the local computer, and frame times measured on an L4 card are converted to the local RTX 5080 by a measured factor of 3.47. A picture costs about $0.134 at the resolution we use. The picture model's limits on speed are described under Limitations.

<!-- 542 vs 596 s, 3.47: #130 comments 2026-10-07T21:57 and 23:02. $0.134: 2099 paper README "What it cost". 250 a day: #130 comment 2026-10-08T03:31. -->

A batch asks for a class of machine, such as one card with 24 GB, and takes whatever the provider has in stock across three zones and three card types, because on 8 October the cheapest type was out of stock in one zone for most of the day. Table G1 compares the same jobs on two card types. An H100 runs ten Pixal3D takes at once in 31 GB of its 80 GB, and makes nearly three times as many models an hour as an L4. It has no ray-tracing cores, so it bakes 2.6 times slower than an L4. Pixal3D therefore takes 80 GB cards first, and a bake takes an H100 only when no other card has been free for five minutes. The L40S was out of stock on both attempts, and the provider's P100 machines started but their driver did not see the card.

**Table G1.** The same jobs on two card types, 8 October 2026. Wait is the time from the order until the machine answers; machine time is the whole rental, setup included.

| Card | Job | At once | Wait | Machine time | Cost | Per take |
|---|---|---|---|---|---|---|
| L4, 24 GB | Pixal3D, 3 close-ups | 3 | 0.4 min | 28.0 min | €0.38 | €0.13, 6.4 an hour |
| H100, 80 GB | Pixal3D, the same 3 | 3 | 0.6 min | 13.9 min | €0.67 | €0.22, 12.9 an hour |
| H100, 80 GB | Pixal3D, 10 close-ups | 10 | 0.6 min | 33.1 min | €1.62 | €0.16, 18.1 an hour |
| L4, 24 GB | bake: 60 surfaces at 3 wear levels | 1 | 0.4 min | 3.8 min (bake 138 s) | €0.05 | |
| H100, 80 GB | the same bake | 1 | 0.6 min | 7.5 min (bake 360 s) | €0.38 | |

<!-- Out of stock most of the day: handoff cloudgame.txt (2026-10-08) and batch logs of that day. Table and paragraph: the cloud ledger rows of batches library-20261008-134330, library-20261008-134449, batch-20261008-134244, batch-20261008-134426 and batch-20261008-141143 (start_wait_minutes, minutes, euros, unit_seconds, peak_gb), summarised in the capacity job's progress log tmp/playtest3/progress-capacity.txt (14:45 table). Close-ups: the wreck's work_lamp, pressure_sphere, ring_frame (3) and ten of its close-ups (10). L40S out of stock: ledger attempts 13:44 and 14:12. P100: setup.log of batch-20261008-134506 ("NVIDIA-SMI has failed"). -->

Since 8 October, every kind of batch is spread over many machines at once: each machine is set up once and takes the next job from one queue as it finishes one, and a batch rents enough machines that each works about as long as its setup takes. Table G2 compares the same batches on one machine and spread. A spread batch ended 1.2 to 2.7 times sooner and cost 4 to 63 percent more, because every added machine spends part of its time setting up.

**Table G2.** The same batches on one machine and spread over several, 8 October 2026.

| Batch | Machines | Time | Cost | On one machine |
|---|---|---|---|---|
| Blender, 6 jobs | 3 L4 | 7.0 min | €0.28 | 14.3 min, €0.20 |
| Library bake, 22 jobs | 4 L4 | 10 min | €0.43 | 27 min, €0.35 |
| Pictures (FLUX.2 klein), 120 | 3 L4 | 5 min | €0.20 | 10 min, €0.14 |
| Pictures without light, 32 | 2 L4 | 4 min | €0.10 | 6 min, €0.08 |
| PartCrafter, 12 runs | 2 L4 | 19.3 min | €0.49 | 35.2 min, €0.47 |
| Shape-check judge, 184 questions | 2 H100 | 16 min | €1.48 | 19 min, €0.91 |
| Qwen-Image-Edit, 16 close-ups | 3 H100 | 11 min | €1.53 | 26 min, €1.24 |

<!-- progress-fleet.txt: "spread runs done" and "Baselines (SCORE_MAX_MACHINES=all=1)" lines; code score bf6688b (spread.py). -->

Table G3 sums the cloud ledger, in which every runner records each machine it rents, by type of machine, from the first batch on 29 September to the end of 8 October 2026. It holds the game 2099's own test and benchmark machines as well as the framework's batches, and the machines of the earliest batches, worth €34.69, were recorded without their type.

**Table G3.** Rented machines by type, 29 September to 8 October 2026.

| Machine | Rentals | Machine time | Cost |
|---|---|---|---|
| L4, 24 GB | 793 | 331.1 h | €266.19 |
| H100 PCIe, 80 GB | 29 | 7.4 h | €21.69 |
| two H100 SXM, 80 GB each | 14 | 1.5 h | €11.03 |
| 32-core processor, 128 GB | 26 | 5.4 h | €9.85 |
| two L4, 24 GB each | 3 | 3.4 h | €5.38 |
| 16-core processor, 64 GB | 13 | 2.3 h | €4.81 |
| 32-core processor, 64 GB | 5 | 0.9 h | €4.26 |
| L40S, 48 GB | 6 | 2.7 h | €4.07 |
| P100, 16 GB | 2 | 0.1 h | €2.44 |
| 16-core processor, 128 GB | 2 | 1.6 h | €1.36 |
| type not recorded | | | €34.69 |
| total | | | €366.76 |

<!-- ~/.farm-factory-props/cloud/ledger.jsonl, rows started before 2026-10-08T22:00Z (midnight CEST), 746 rows from 2026-09-29T10:07Z; machines[].type, minutes, euros summed; rows without machines[] summed as "type not recorded". Types: L4-1-24G, H100-1-80G, H100-SXM-2-80G, POP2-32C-128G, L4-2-24G, POP2-16C-64G, POP2-HC-32C-64G, L40S-1-48G, RENDER-S, POP2-HM-16C-128G. -->

::: gap
**Gap: cost tables.** These tables will give the cost per kind of batch and per world, reconciled with the cloud provider's bill. They wait on the worlds and on the bill; the figures per place so far (Appendix B) are lower bounds taken from the build logs.
:::
