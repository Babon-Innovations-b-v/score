---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 12 October 2026"
abstract: |
  Games, films and robot training need 3D worlds that are complete, editable and owned by the people who make them. World models and one-shot 3D generators can produce a convincing place from a sentence or a picture, but they give frames that no engine can open, or one fused scene without separate objects or clear rights. Studios have always built worlds in stages, from concept art and layout to modelling, surfacing, sound and review. We present SCORE, a world generation framework that keeps these stages and automates large parts of them with open vision foundation models, procedural tools and coding agents, while the creator chooses and reviews. Because every stage's output is kept, the creator can rerun or fix any single stage, and because every model allows commercial use, the creator stays the author of the result, holding its full commercial rights. We are building SCORE's first world, the game world of 2099, only 3 of whose 18 places passed its completion gate when it was last measured, and plan three further worlds of different kinds. Our aim is to show that checkable stages, with open models for shape and closed, paid models for pictures and surfaces, can build worlds that a creator owns and keeps editing. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT license).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main text: the three contributions only (the staged framework, its mechanisms, the evidence),
    about 4 to 5 pages plus references while gaps are open. The appendix holds only the evidence
    behind a claim the main text makes.
  - Every number is read from a file named in a comment beside it. "Local R&D log" means the
    build sessions' own logs, to be published with the framework.
  - The world step is one optional step; no result compares it with another model or judges it
    on its own, and its output is credited "Generated using World Labs".
-->

```{=latex}
\makeatletter\def\fps@figure{t}\makeatother
```

::: gap
**Gap: teaser figure.** This figure will show four worlds made with SCORE: the game world of 2099, a stylised underwater world, a simulation world for robots, and a third-person fantasy world. Each will appear as its chosen concept beside the finished world in its engine. It waits until the four worlds are finished and accepted by their creators.
:::

# Introduction

Interactive 3D worlds are the raw material of games, film and embodied AI [@yang2024holodeck], and building one is expensive: every object has to be modelled, surfaced, placed, given collision, lit and given sound in one style, and the world has to stay editable. Generative models promise to take over much of this, but in GDC's 2026 survey 52 percent of game workers thought generative AI was hurting the industry [@gdc2026survey]; a tool for building worlds has to leave the result in the creator's hands.

World models generate a world as frames [@bruce2024genie; @genie3] that no engine can open. 3D world generators [@wang2025worldgen; @hyworld2] produce geometry, but mostly as one fused asset, from which separate objects are recovered after the fact [@hu2026worldact; @niu2026worldsculpt]. Both work in one shot, so a creator cannot find or change the step behind a fault. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] and coding agents that write scenes as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue] keep the world explicit, but rebuild a scene that already exists or draw their objects from a fixed library, and such agents judge their own geometry unreliably [@li2026lego]. Open vision foundation models [@oquab2023dinov2] now read shapes [@li2026pixal3d], masks [@carion2025sam3], depth [@wang2025moge2] and parts [@lin2025partcrafter] out of pictures, and a coding agent can connect them as tools; none of them provides is one style across objects that different models made, which the field names as an open problem [@wu2026production; @yang2026flowscene].

Studios build worlds in stages, each with an output a person can check. SCORE keeps these stages and automates large parts of them with the models above, procedural tools and coding agents, while the creator chooses and reviews. Its worlds are **complete**: every object, surface, light and sound exists wherever the player looks. They are **owned**: every model in the framework allows commercial use of its output, so the creator stays the author, holding the full commercial rights. They are **responsive**: every object has real collision, mass and material. And they can be any kind of **environment**. To our knowledge, no other openly available world generation work joins vision foundation models into engine-ready scenes that are built from reference pictures, steered by a person's choices at each step, and made only with models that allow commercial use of their output.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Hand-off pattern: material/11-vision-foundation-models.md. -->

This paper makes three contributions:

- **The SCORE framework:** staged, retraceable generation from a creator's choices to one canonical scene: a generated base layer under the creator's edit layers (Section 2).
- **Mechanisms that keep worlds coherent and faults cheap:** checks before every paid stage, a parts check, a shared surface library that keeps shape and surface apart, and review tools (Section 3).
- **Evidence from four worlds of different kinds**, and a shared benchmark (Section 4).

# The framework

![The stages on the hub of the game 2099: (a) the concept the creator chose, (b) the plan in metres, (c) part of the inventory, (d) two close-ups, (e) one library surface at three wear settings, (f) the room in the game engine.](figures/fig-overview.jpg){width=70%}

<!-- Hub concept C12, plan v3, inventory data/inventory/hub.json, close-ups hubrefs/c12/clean, swatches robust-exp/img, shot robust-exp/r6/shots/now/wide-south. -->

Figure 1 shows the stages on one place, from the creator's concept to the assembled room. Every stage's output is kept, so the creator can trace a weak result to its stage and rerun or fix that stage alone. Appendix C lists every model, its licence, and what was automatic or done by hand.

**Inventory.** A coding agent cuts the concept into tiles and lists every visible element, and each element becomes a row, with its kind, anchor, size and count, or is dropped with a written reason. Nothing is made or placed that is not a row.

<!-- Rule: the owner's rule of 2026-10-08; issue #130, 2026-10-07T23:04. -->

**Close-ups.** Every inventory row gets a close-up, a picture of the object alone, drawn from its crop of the concept by an open model, Qwen-Image-Edit-2511 [@qwenimageedit]; only a close-up that fails the shape check (Section 3.1) is redrawn by a closed one, Nano Banana Pro [@nanobananapro].

<!-- Stage: tools/props/closeup/stage.py and check.py (score d323674, 87e5ffb); the owner's decision of 2026-10-08 (briefs/score-common.txt, CLOSE-UPS). -->

**Models.** Each object is built by a code builder that a coding agent writes or generated from its close-up by Pixal3D [@li2026pixal3d], as the parts check decides (Section 3.2). Every real-world object becomes one model: a console becomes a desk carrying separate monitors and keyboards. Models give shape only (Section 3.3). Outdoor ground follows a plan of flat areas and paths, with landforms from a picture drawn over it.

**The canonical scene.** Every place is one OpenUSD stage [@openusd] in which each object carries its kind, its transform in metres, its collision and the library surface of each part, together with the room's shell, the ground, the backdrop, the lights and the cameras the place is judged from. The generated base layer lies under an edit layer that belongs to the creator, so an edit survives when the base is generated again (Figure 2).

![The wreck as an OpenUSD stage: (a) in the game; (b) rendered in Blender from the same camera; (c) Blender's object outlines over the game's picture; (d) after an edit in the edit layer (cover moved, hull given another surface) and a regenerated base.](figures/fig-usd.jpg){width=60%}

<!-- Wreck stage: tools/usd/export.py on data/kit/wreck.json; renders by tools/usd/views.py (Blender 5.0.1, headless); the edit survival is checked by tools/usd/export_test.py. Scene record: tools/usd/scene.py, builders.py, data/scene/<place>.json (score f51d92b, 2708ff2, 3a28fe7). -->

**The other layers.** The same stage holds the rest of what makes a place complete, each in a layer of its own: people, as skinned characters that a chain of open models makes from a picture or a few words; sound, generated by MOSS-SoundEffect [@moss2026] and tied to surfaces, rooms and objects; motion, as time samples; particle effects; and shaders, baked into pictures any USD reader can draw. Every stage that loads a model runs as a batch on rented cards that are deleted afterwards, or as a job on a Kubernetes cluster.

<!-- Casts and the character maker: tools/characters (skel_usd.py, cast.py, maker/make.py). Sound: tools/usd/sound.py. Motion: tools/usd/motion.py. Effects: tools/usd/effects.py. Shaders: tools/usd/shaders.py. Runners and the cluster path: tools/cloud/CLAUDE.md, tools/props/cloud. -->

::: gap
**Gap: the scene in a game engine.** The same stage loaded in a game engine with its collision, surfaces, mass and friction. It waits on the game engine adapter.
:::

# Mechanisms

## Checks before spending

Deterministic checks run before every stage that costs money, because a fault is free to fix in the plan and costly once built. They test real geometry: light leaks, blocked openings, doors, open, thin or leaning models, and colours off the palette. The close-ups' shape check measures framing and outline, and an open vision-language model, Qwen3.8-27B [@qwen38], compares each picture with its crop; it leans towards failing, because a wrong picture that passes costs a bad 3D model (Appendix C). Loose objects are dropped in a physics simulation, and one that would move further than a small limit fails the resting check, because a large move is a fault of the layout. A failed check sends the work back one stage (Appendix B).

<!-- Close-up check: tools/props/closeup/check.py. Settling and the resting check: tools/usd/settle.py, resting.py (score e5d829c). -->

Coding agents judging their own scenes agree with a measured score on geometry only 45.8 percent of the time [@li2026lego], so a completion gate passes a place only when every inventory row has its object or a written reason, nothing visible stands in for a made piece, no resting fault is left, every model the creator picked is still the one shown, and every check ran on the stage as it is now; unknown blocks like fail, and a hook refuses to end an agent's session that claims a place is done while its gate does not pass.

<!-- Gate and picks: tools/usd/complete.py, picks.py; .claude/hooks/completion_guard.py (score 7ee78fc, 1ba8b74, ff44157, 1a1ce30). LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. -->

## The parts check

![The parts check: four close-ups (top) and the objects as built (bottom). The notice board and locker are built in code, whose builds show every part; the microscope and chair are generated with Pixal3D.](figures/fig-parts-check.jpg){width=70%}

Picture-to-3D models build chunky solids well, but flat panels, thin beams and openings badly, while code builders are exact but show only the parts the coding agent wrote. For each kind of object, the parts check renders a code build from the front: if every part of the close-up is visible in it, the kind is built in code, and otherwise it is generated and made solid (Figure 3).

::: gap
**Gap: the parts check's order.** A queued change makes the parts check try generation first; this section is rewritten when it lands.
:::

## Shape and surface apart

![(a) Three library surfaces at wear 0, 0.4 and 0.8. (b) The hub's tool board with each piece's own picture colours (left) and with library surfaces, one model per tool (right).](figures/fig-surfaces.jpg){width=70%}

Every part of every object takes one surface from a shared library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette and worn only where wear has a cause, such as edges (Figure 4a, Appendix D). PartCrafter [@lin2025partcrafter] splits a generated model into parts, and an open vision-language model, shown each part outlined on the close-up, names its library surface; the picture's colours are not kept. When each piece kept them, every piece brought its own rust and stains (Figure 4b); with shape and surface apart, the hub became consistent and the creator accepted it (Appendix A).

::: gap
**Gap: painting beyond the hub.** On the rest of world 1 the painting is not yet consistent (Limitations). The surface stage's new method, to be measured there, is the finish-map route: Gemini 3.1 Pro [@gemini31pro] lists a model's finishes on its close-up and names a library surface for each, Nano Banana Pro draws the close-up again with one flat colour per finish, and SegviGen [@li2026segvigen] lays that map onto the shape.
:::

## Review tools

A review page, built only from the files the stages wrote, shows each stage's output, before-and-after shots from the same cameras, every check's result, and the stage rendered by Blender along a walk through it. An optional world step can turn the concept into a walkable room to show what the concept does not; nothing it produces is shipped.

<!-- Review page: tools/review/page.py and tools/review/CLAUDE.md (score f51d92b). -->

# Evidence

We build four worlds with the same stages: the game world of 2099 (a Moon base, a camp on Mars and a prologue on Earth), a stylised underwater world, a simulation world for robots, and a third-person fantasy world.

::: gap
**Gap: Table 1, results per world and stage.** Per world: places, time, cost, models built in code and generated, and faults caught before spending against those found after. It waits on the creator's acceptance of each place; worlds 2 to 4 are not started.
:::

::: gap
**Gap: figure of world 1.** Places of world 1 from its current run, rendered from their stages beside their concepts, and later one place of each further world. It waits on the creator's review of that run.
:::

::: gap
**Gap: LEGO-Bench, ablations and style.** Scores on LEGO-Bench [@li2026lego]; runs with and without the world step and the checks; whether a place keeps one style. They wait on the benchmark's code and the surface stage's reviewed results.
:::

<!-- Style measure: tools/review/style.py and its test style_test.py (score d859e5d, 7a8ec4b, 2ca5ba4, 453e06d). -->

**With and without the agent tools.** On two of three places of world 1, an agent with the completion gate and its tools used about half the output and cost of one without them; on the third, the one without left fewer faults. Each arm ran once (Appendix E).

<!-- paper/evidence/agent-tools-bench/analysis.json; Table E1. -->

# Limitations

- **One creator, one world so far, and that world not yet accepted.** Every verdict is one creator's. When last measured, only 3 of world 1's 18 places passed their own completion gate, and the creator has accepted one place, the hub.
- **Code builders do not scale, and places come out sparser than their concepts.**
- **Two stages depend on closed, paid models.** Nano Banana Pro draws the concepts and every close-up that the open model's pictures fail; on the last 17 close-ups of world 1, none of the open model's pictures passed the shape check (Appendix C). The surface stage uses two of Google's models: Gemini 3.1 Pro lists each model's finishes on its close-up and names their library surfaces, and Nano Banana Pro draws the finish map that SegviGen lays onto the shape. A public framework thus depends on closed services for two of its stages. Their daily limits set the pace of world 1, and they can change their price or be retired, which limits reproducibility. An open-model fallback for both stages is future work.
- **Parts do not follow finishes, and shadow reads as paint.** A finish without its own part, such as a gold foil patch on a white hull, is lost when the part is painted with one surface, and the judge reads shadow on the close-up as dark paint.
- **Objects are physical but not interactive.**

<!-- Gate: 3 pass, 14 fail, the tube unknown, with the gate of 2026-10-10: https://github.com/Babon-Innovations-b-v/score/issues/1#issuecomment-6099330150. Concept-density check: issue #130. Surface stage's paid asks: score/stages/surfaces/finish_ask.py (LIST_MODEL gemini-3.1-pro-preview, MAP_MODEL gemini-3-pro-image) and segvigen_row.py; the finish-map method chosen by the owner on 2026-10-12 (score/stages/surfaces/CLAUDE.md). Parts and shadow: https://github.com/Babon-Innovations-b-v/score/issues/1#issuecomment-6092393485. -->

# Future work

Building the three further worlds; a game engine adapter that writes mass and friction; interactable objects, which robotics needs; a surface stage that holds on world 1; open close-ups that pass the shape check more often; and LEGO-Bench [@li2026lego].

# Conclusion

SCORE builds worlds from a creator's choices in checkable stages whose outputs are kept. On its first world, the parts check, one model per real-world object and the shared surface library made one room, the hub, consistent enough for its creator to accept it. Only 3 of that world's 18 places passed the completion gate when last measured; whether the framework holds across a whole world, and across kinds of worlds, is what the remaining places, worlds and the benchmark will show.

# References {-}

::: {#refs}
:::

# Appendix {-}

```{=latex}
\appendix
```

# The hub in six rounds

The mechanisms of Section 3 came out of six rounds of work on the hub on 6 and 7 October 2026, each answering the creator's verdict on the round before (Table A1). In the first two rounds, he chose between the old and the new method side by side from the same cameras.

**Table A1.** The hub's six rounds. Cost is given as rented GPU time in euros and picture-model calls in dollars. Frame time is the mean frame time on an RTX 5080, in the night scene, at 1600×900.

| Round | Change | Creator's verdict | Cost | Frame time |
|---|---|---|---|---|
| 1, two walls, A/B | surface library, routing by shape, room checks | chose the new method ("Y looks much cleaner") | €0.88 | 7.81 ms vs 7.53 |
| 2, two walls, A/B | 71-variant library, shared texture sets, roof check | chose the new method again | €1.70 | 8.05 ms vs 8.24 |
| 3, whole room | all stages end to end, 74 models | old models were still loaded; labels and floor fittings were wrong | €1.67 | 6.78 ms (old 9.22) |
| 4, whole room | detail through the pipeline, picture colours kept | "pretty much all of this became messy" | €8.50, $5.09 | 9.6 ms |
| 5, eight pieces, A/B | shape only from the pipeline, library surfaces, parts check | new method preferred for the door, notice board and porthole; three pieces still wrong | €0.21 | not run |
| 6, whole room | round 5 everywhere, one model per object, straightness check | "this looks amazing, I have no negative feedback" | €3.48, $1.07 | 5.6 ms |

<!-- R1: local R&D log progress-robust-exp.txt [A/B numbers], blind key, quote at "ROUND TWO". R2: [A/B round two], [spend round two]; session record 2026-10-06T16:52Z. R3: progress-robust-exp.txt round three and fix round. R4: progress-hub-r4.txt; #130 comment 2026-10-07T05:29; quote in brief job-hub-r5-test.txt. R5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt. R6: progress-hub-r5.txt ROUND SIX; #130 comments 2026-10-07T15:55 and 16:20. -->

Three findings shaped the method. First, deterministic checks catch what agents miss: in round one, the share of rays leaking out through walls and roof fell from 1.53 percent of 5,817 to zero, and the colour noise within surfaces from a median of 31.1 to 3.2 percent, but only walking through the loaded room showed 26 old models still in it, which became the made-only check. Second, generated pieces that kept their pictures' colours made the room inconsistent, so surfaces come only from the library. Third, generated composite objects melted their parts together, and generated boxes leaned (one locker by 13 degrees), which led to one model per real-world object and to the straightness check (Figure 4b). By round six the room used 0.45 million triangles, against 1.96 million in round four, and 187 MB on disk, against 487 MB.

<!-- Numbers: progress-robust-exp.txt [A/B numbers] and round three fix round; 2099 docs/bible.md item 11 (locker); #130 comment 2026-10-07T15:55 (round six vs four). -->

# Check details

- **Room checks** cast rays to find light leaking out through walls and roof, find pieces in front of a real opening and roof and wall fittings more than 3 cm off their surface or turned more than 5 degrees from it, and count pieces, triangles and lamps against the room's budget.
- **Door check:** every door must stand in a wall or partition that fully separates its two sides, tested by walking a grid from one side to the other.
- **Parts check:** in the code build, every part shown in the close-up must be at least 10 percent visible from the front, and no label may cover a part.
- **Model check:** every model must be a closed solid with walls at least 3 mm thick. A generated box fails if one of its sides tilts more than 2 degrees or is warped. Making a generated model solid stops if its bounding box grows more than 3 percent.
- **Palette sweep:** every model's colours are compared with the place's library palette.
- **Made-only check:** in the engine, any visible mesh that the framework did not make fails. A made-only finding can never be waived.
- **Close-up shape check:** the picture needs a plain border all round, one object filling a sensible share of the frame, and an outline within a set proportion of the inventory row's box. The judge's seven questions (among them one object, a clean background, the whole object, the same object, no parts missing or added, the right proportions) each pass by a majority of three answers sampled with different seeds. A close-up passes only when both halves pass.
- **Settling and resting check:** an object that would turn more than 15 degrees or drift more than 30 cm when dropped keeps its laid pose and is marked as not resting; small debris, with no side over 1.4 m, may turn freely and drift up to 1 m. Hung objects are exempt by their inventory anchor, and fixed objects are not judged for tipping.
- **Completion gate:** the requirements given in Section 3.1, each with its result tied to a fingerprint of the stage's files and inputs; a result made on another stage counts as unknown. The placeholder check judges every mesh a code builder draws, and only the shell builders pass unnamed.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). Close-up check: tools/props/closeup/check.py. Settling and resting: tools/usd/CLAUDE.md, settle.py, resting.py (15 degrees, 30 cm; debris 1.4 m, 1 m). Placeholder check widened to every code-builder mesh: score 6364971. -->

# Models and licences

Every model in the framework must allow commercial use of its output (Table C1); we read each licence for its clauses on commercial use. Candidates were dropped under this rule, among them NVIDIA's Lyra 2.0 (weights for internal research only), Hunyuan3D 2.1 (licence does not apply in the European Union) and GarmentCode's fork of NVIDIA Warp (non-commercial research only), which Newton's cloth solver on upstream Warp replaced; Blender's cloth simulation [@blender] is kept as a second route. The one open doubt is the face LoRA, whose training data is not disclosed.

**Table C1.** Models in the framework.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups the open model fails, ground skins | paid API |
| Nano Banana Pro [@nanobananapro] | finish maps: the close-up drawn again with one flat colour per finish | paid API |
| Gemini 3.1 Pro [@gemini31pro] | each model's finishes listed on its close-up, and their library surfaces named | paid API |
| Qwen-Image-Edit-2511 [@qwenimageedit] | close-ups, first | Apache-2.0 |
| Qwen3.8-27B [@qwen38] | the close-ups' shape check; each part's material | Apache-2.0 |
| Pixal3D [@li2026pixal3d] | picture to 3D | MIT; DINOv3 licence [@simeoni2025dinov3] for its encoder |
| PartCrafter [@lin2025partcrafter] | parts | MIT; its non-commercial background remover not used |
| SegviGen [@li2026segvigen] | lays the close-up's finish map onto the 3D shape (surface stage) | MIT, on TRELLIS.2 (MIT); DINOv3 licence for its encoder; its non-commercial background remover and nvdiffrast not used |
| GeoSAM2 [@deng2025geosam2] | parts of our own model, seeded by the close-up's regions (trial) | Apache-2.0 |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surfaces | BSD-3-Clause |
| MOSS-SoundEffect v2.0, CLAP | sound | Apache-2.0 |
| World Labs [@marble_terms] | optional world step | paid; outputs owned by paid users |
| FLUX.2 klein 4B [@flux2klein] | earlier prop pictures; the characters' A-pose pictures from words and their hair's clay pictures | Apache-2.0 |
| MoGe-2 [@wang2025moge2], SAM 3 [@carion2025sam3] | measuring and finding objects in pictures | MIT; SAM Licence |
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

The close-ups' shape check was tuned on 40 close-ups that four open picture models drew of the lab's ten objects, each scored by hand, and on Nano Banana Pro's ten pictures of the same objects. With the majority of three sampled answers, the check agreed with the hand score on 29 of the 40, passed all ten of the closed model's pictures and two marginal ones, passed none scored wrong or failed, and failed nine that were good or usable. The judge's single answer at temperature zero was rejected: asked the same 51 questions twice in one batch, it changed its verdict on 7. On the lab, 7 of the closed model's first pictures failed for drawing the room or dimension lines around the object, and all 7 passed when redrawn from the crop alone. Table C2 gives the stage's runs on world 1.

**Table C2.** The close-up stage on world 1. Cloud is rented card time in euros; the closed model's pictures are in dollars.

| Run | Close-ups | Open model accepted | Closed model accepted | Left for the creator | Cloud | Closed model |
|---|---|---|---|---|---|---|
| Lab, 22 rows (earlier check: one answer) | 22 | 8 | 14 | 0 | €4.12 | $2.81 |
| World 1's remaining rows (three places) | 17 | 0 | 10 | 7 | €3.06 | $4.02 |

<!-- Tuning: progress-openpics.txt 18:53 (vote: 29/40 agree, 0 wrong/failed passed, 2 marginal passed, 9 wrong fails; Pro 10/10), greedy rejected 17:56 (7/51 differed). Lab: progress-openpics.txt 17:35 (8 Qwen, 14 Pro, 7 Pro first takes failed for the room or dimension lines, all crop-only retakes passed, EUR 4.12 cloud, $2.81 Pro). World 1: progress-world1-score.txt 18:55 (workshop, greenhouse, campgrounds; 17 rows) and 20:12 (10/17 accepted, all by Pro, Qwen 0/17, 7 for review, EUR 3.06, Pro $4.02). -->

The picture-to-3D step, the part splitting, the surface bakes, the sound generation, all checks and the assembly run automatically. Coding agents (Claude Code [@claudecode]) write the plans, the inventories and every code builder; in the hub's final round, 86 of its 98 models were built in code. Some steps were still done by hand: some generated objects were turned to face the right way by eye, and a few labels were placed by hand before a rule took over that job. The concepts and the verdicts are the creator's own choices.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. Characters' licences: the characters' licence check of job characters-full, 2026-10-09 (progress-characters-full.txt 12:56, the coordinator's brief to the paper agent), recorded in tools/props/cloud/characters_setup.sh and tools/characters/maker/CLAUDE.md; Hugging Face licence tags of FLUX.2-klein-base-4B, refcontrol-FLUX.2-klein-4B-reference-depth-lora (apache-2.0) and VAST-AI/UniRig (mit), read 2026-10-09; SAM3DBody-cpp LICENSE (MIT). -->

# The surface library

The surface library holds families of variants: painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light and print. After the hub's second round it held 71 variants made from 14 ProcFunc recipes. Each variant is a recipe with settings, takes its colours only from the palette, and is baked into base-colour, metal-roughness and normal maps at a texture density that depends on how close the player can get. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor that a piece stands on.

<!-- 71/14: progress-robust-exp.txt round two. Kick wear 32 cm: 2099 docs/bible.md item 11. -->

# With and without the agent tools

The tools that check an agent's work were tested on three places of world 1: a room (the workshop, 814 objects), an outdoor place (the street, 1,198 objects) and a dense room (the hangar, 1,657 objects). They are the completion gate (Section 3.1); a triage of the resting check, which judges each object by what holds it up, read from its inventory row, and keeps only real faults [@tam2025sceneeval; @xia2026sage]; a pick lock, which refuses an export that would show anything but the model the creator picked for a row; and a render-and-compare, which lists the objects least like their close-ups by DINOv2 similarity [@oquab2023dinov2]. In both arms, the same agent (Claude Opus 5.5 in Claude Code, headless) started from the same exported stage and inventory and was asked to make the place as complete as it could in about 50 minutes, through its layout data only; one arm had the framework from before these tools. Each arm ran once, so Table E1 shows what happened, not an average.

**Table E1.** One session per arm and place. Faults are the resting triage's real faults left on the final stage, measured against the arm's own data; placeholders by the first placeholder check; rows are inventory rows with no object and no written reason. Agent cost is the session's model cost; cloud is its rented machines' cost.

| Place, arm | Real faults (start → end) | Placeholders | Rows missing | Minutes | Agent cost | Output tokens | Cloud | Exports | Gate said unknown |
|---|---|---|---|---|---|---|---|---|---|
| Workshop, without | 18 → 13 | 0 → 0 | 1 → 0 | 36 | $2.26 | 30.4k | €0.85 | 7 | not used |
| Workshop, with | 18 → 0 | 0 → 0 | 1 → 0 | 26 | $1.42 | 14.3k | €0.85 | 2 | 2 of 4 calls |
| Street, without | 11 → 0 | 0 → 0 | 0 → 0 | 38 | $2.40 | 30.0k | €0.32 | 9 | not used |
| Street, with | 12 → 0 | 0 → 0 | 0 → 0 | 39 | $1.21 | 10.4k | €0.76 | 1 | 0 of 5 calls |
| Hangar, without | 14 → 4 | 5 → 0 | 0 → 0 | 47 | $2.01 | 26.6k | €0.00 | 7 | not used |
| Hangar, with | 14 → 9 | 5 → 0 | 0 → 0 | 32 | $2.34 | 29.1k | €0.64 | 5 | 3 of 6 calls |

The tools made building cheaper more often than they made the scene better. On the workshop and the street, the arm with the tools used about half the agent's output and cost, and exported the stage once or twice instead of seven to nine times, because the triage named the few real faults among hundreds of alarms. On the workshop, 13 of its 18 faults were cleared by writing into the inventory what holds a piece up, which the creator still has to confirm. On the hangar the arm without the tools left fewer faults: the arm with them spent its time replacing five placeholder slabs and trying the drop test, which failed on a room with no ground mesh (fixed after the run), and the nine faults it left are models with stray parts below their feet. No agent claimed a place was complete, so the gate's hook never had to refuse a claim. No row carries an owner's pick, so the pick lock was not tested.

<!-- Benchmark: paper/evidence/agent-tools-bench: analysis.json (written by the bench's analyse.py from each session's record and transcript), and per arm and place (on = with, off = without) measure-start.json, measure-end.json, measure-manual.json and session.json. Arms: without = score 672ddfd, with = ff44157 (both with ff44157's data for the three places); claude -p --model claude-opus-5-5, 2026-10-09. The street's start reads 11 and 12 because the two start measures read the inventory from different checkouts; the stage was the same. The workshop's 13 cleared by data: 11 tool-board tools set to hanging, two arm monitors fixed (session report). -->
