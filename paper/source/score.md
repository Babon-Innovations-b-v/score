---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 9 October 2026"
abstract: |
  Games, films and robot training need 3D worlds that are complete, editable and owned by the people who make them. World models and one-shot 3D generators can produce a convincing place from a sentence or a picture, but they give frames that no engine can open, or one fused scene without separate objects or clear rights. Studios have always built worlds in stages, from concept art and layout to modelling, surfacing, sound and review. We present SCORE, a world generation framework that keeps these stages and automates large parts of them with open vision foundation models, procedural tools and coding agents, while the creator chooses and reviews. Because every stage's output is kept, the creator can rerun or fix any single stage, and because every model allows commercial use, the creator stays the author of the result, holding its full commercial rights. We demonstrate SCORE on the game world of 2099 and plan three further worlds of different kinds. Open models, working in checkable stages, can build worlds that a creator owns and keeps editing. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT license).
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

Interactive 3D worlds are the raw material of games, of film and of embodied AI, where agents are trained and tested in simulators [@yang2024holodeck]. Building such a world is still expensive. Every object has to be modelled, given surfaces, placed, given collision and physical properties, lit and given sound, all in one consistent style, and the world has to stay editable while the project changes. Generative models promise to take over much of this work, but the people who would use them are wary of it: in GDC's 2026 survey, 36 percent of game workers used generative AI at work, and 52 percent thought it was hurting the industry [@gdc2026survey]. Taking over the work is therefore not enough: a tool for building worlds has to leave the result in the creator's hands.

Two lines of research generate the world itself. The first, learned world models, generates it as frames. Genie learns an interactive environment from video [@bruce2024genie], and Genie 3 renders a world that a person can move through in real time; its announcement lists a constrained range of actions and a few minutes of continuous interaction among its limits [@genie3]. Nothing that these models produce can be opened in a game engine or an editor, and their world exists only as far as the player looks. The second line, 3D world generators, produces geometry instead. WorldGen turns a text prompt into a traversable scene for standard game engines [@wang2025worldgen], and HY-World 2.0 turns text or a picture into a single splat or mesh world [@hyworld2]. Most such outputs, however, are "static monolithic assets with limited editability and physical interaction" [@hu2026worldact], and WorldAct and WorldSculpt address this by recovering separate objects from them after the fact [@hu2026worldact; @niu2026worldsculpt]. In both lines the world is generated in one shot. When part of the result is wrong, the creator can regenerate the whole world or repair it by hand, but cannot see which step caused the fault, and cannot change that step alone.

A third line of work keeps the world explicit. Infinigen and Infinigen Indoors build every asset from procedural rules, with materials as generators of their own [@raistrick2023infinigen; @raistrick2024indoors]. This gives real geometry and full control, but only over the content that the rules describe. Holodeck has a language model write layout constraints, which a solver then satisfies with assets retrieved from a library [@yang2024holodeck]. SceneCraft, recursive code world models, WorldClaw and AutoUE let coding agents write scenes, or whole games, as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue]. LEGO-Anything shows what such agents need. When coding agents rebuild a scene from a single picture, they start weakly, undo their own progress while editing, and judge their own geometry unreliably; giving them grounded tools, rather than training them further, closes much of that gap [@li2026lego]. All of these systems, however, either rebuild a scene that already exists or draw their objects from a fixed library of assets.

Meanwhile, each of the parts that a world needs can now be read out of pictures by an open model. Vision foundation models learned the world from images in the way that language models learned it from text [@oquab2023dinov2]. They can now turn a picture into a 3D shape aligned with its pixels [@li2026pixal3d], into a mask for each named object [@carion2025sam3], into depth in metres [@wang2025moge2; @yang2024dav2], into the parts of an object [@lin2025partcrafter] or into a human body [@yang2026sam3dbody]; related models turn a sentence into motion [@rempe2026kimodo] or into sound [@moss2026]. Most of these models pass on pictures, masks, depth maps or meshes rather than their internal features, so a coding agent can connect them to one another as it would connect tools. What none of them provides is one consistent style across objects that different models have made. The field names this as an open problem [@wu2026production; @yang2026flowscene], and Hunyuan3D Studio addresses it only by restyling the input picture [@lei2025hunyuanstudio].

Studios have always built worlds in stages: concept art, layout, asset lists, modelling, surfacing, sound and review. Each stage has a clear output that a person can check before the next one starts, which makes this way of working the natural basis for a world generation framework. SCORE keeps these stages and automates large parts of them with the models above, with procedural tools and with coding agents, while the creator chooses and reviews. Its name states what it aims for. The worlds it makes are **complete**: every object, surface, light and sound exists wherever the player looks, and everything that the world's core mechanics need, such as collision, the doors that open and the sounds that play with them, is made when the world is built rather than added later. They are **owned**: the creator decides what the world is and stays the author of the result, holding its full commercial rights, because every model in the framework allows commercial use of its output. They are **responsive**: the world answers to the physics engine that loads it, because every object has real collision, mass and material, so it behaves physically in any engine or simulator, under physics that each world may set for itself, such as the low gravity of the Moon. And they can be any kind of **environment**, real or made up. SCORE does not compete with procedural tools, part splitters or world generators; it takes them in as building blocks wherever their licences allow. It also does not generate a world in one shot: the creator chooses the style, the concepts and the storyboards up front and reviews each stage, and coding agents and models do the work of the stages between those choices.

What a creator gets from this can be used today. A world comes whole, with its people and machines animated by motion that the framework generates from sentences or that the creator has captured. It is one OpenUSD stage, which opens in the tools that artists and engineers already use, and its people are built with SAM 3D Body and moved with Kimodo, open models made for robotics and simulation as well as for entertainment, so its bodies and clips carry straight into robotics work. A creator drives the framework with a coding agent's help rather than by learning each of its tools. And because every heavy stage runs from pinned container images on rented cards or on any Kubernetes cluster, a cloud provider could offer the framework as a product. To our knowledge, no other openly available world generation work joins vision foundation models into engine-ready scenes that are built from reference pictures, steered by a person's choices at each step, and made only with models that allow commercial use of their output.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Hand-off pattern: material/11-vision-foundation-models.md. -->

This paper makes three contributions:

- **The SCORE framework:** staged, retraceable generation from a creator's choices to one canonical scene, which consists of a generated base layer and the creator's own edit layers (Section 2).
- **The mechanisms that keep its worlds coherent and make faults cheap to fix:** deterministic checks before every stage that costs money, a parts check that decides how each object is built so that every real-world object becomes one model, a shared library of rule-based surfaces that keeps shape and surface apart, and review tools for the creator (Section 2).
- **Evidence from four worlds of different kinds:** the time, the cost and the faults caught before spending at every stage, and an evaluation on a shared benchmark (Sections 3 and 4).

# Methods

![The stages on one place, the central hub of the game 2099. (a) The concept, drawn by a picture model from the creator's reference pictures and chosen by the creator. (b) The dimensioned plan in metres, with walkways and standing spots. (c) An excerpt of the scene inventory, which has 74 rows. (d) Close-up pictures of two objects. (e) One surface from the shared library of rule-based surfaces at three wear settings. (f) The assembled room in the game engine.](figures/fig-overview.jpg){width=100%}

Figure 1 shows the stages on one place. The creator chooses a concept (a), and a coding agent turns it into a dimensioned plan (b) and a scene inventory (c). An open picture model draws a close-up of every object in the inventory, and a closed one redraws those that fail a shape check (d). Each object is then built in code or generated in 3D, its parts are painted from the shared library of rule-based surfaces (e), and the place is assembled in an engine (f). The output of every stage is kept, so the creator can trace a weak result to the stage that caused it, rerun or fix that stage, and regenerate the stages after it while keeping their own edits. The sections below describe each stage with an example. Every stage that loads a model runs as a job in a pinned container image on rented cards, either on single machines or on any Kubernetes cluster (Appendix G).

<!-- Hub concept C12, plan v3, inventory data/inventory/hub.json (74 rows), close-ups hubrefs/c12/clean, swatches robust-exp/img, shot robust-exp/r6/shots/now/wide-south. -->

## Inventory as a partition of the concept

![The inventory of the lab on the Moon base, built from its concept. Left: the concept, cut into twelve tiles. Right: examples of how each visible element maps to an inventory row, or is dropped with a written reason. Of the 47 elements in this concept, 40 were mapped to inventory rows and 7 were dropped with a written reason.](figures/fig-partition.jpg){width=100%}

The inventory decides what exists in a place. A coding agent cuts the concept into tiles and lists every visible element, and each element either becomes a row (with its kind, anchor, size and count) or is dropped with a written reason (Figure 2). Nothing is made or placed that is not a row. After the build, the place is rendered from the concept's own camera and compared with the concept; a place that is clearly sparser than its concept fails this concept-density check.

<!-- place-lab/tools/elements.json: 47 elements, 7 dropped. Rule: the owner's rule of 2026-10-08; issue #130, 2026-10-07T23:04. -->

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

A place is complete only when its evidence says so. Coding agents judging their own scenes from renders agree with a measured score on geometry only 45.8 percent of the time, below chance [@li2026lego], and ours called places finished that the creator then found unfinished. SCORE therefore computes completeness instead of asking for it. A completion gate passes a place only when every inventory row has its object on the stage or a written reason for dropping it, nothing visible stands in for a made piece, no real resting fault is left, every model the creator picked is still the one shown, every check was run on the stage as it is now, and the review page was rendered from that stage. Every check answers pass, fail or unknown, and unknown blocks like fail, as in LEGO-Anything's validator; a hook in the agent's harness refuses to end a session that claims a place is done while its gate does not pass. The resting check became a triage. Each object is judged by what holds it up, read from its inventory row (the floor, a wall, the ceiling, the object it stands on, a hook it hangs from, or the kit's own frame), with SceneEval's guards against false alarms [@tam2025sceneeval]: an overlap counts only if it survives moving the object 5 mm away, and a standing object needs four contact points with its weight inside them. Cables, cloths and rubble may sink into what they lie on by an amount kept as data, and a loose object that moves more than 0.2 m or turns more than 8 degrees when dropped does not rest as laid, after SAGE's stability rule [@xia2026sage]. The real faults are grouped by cause, each group with one close-up aimed at its worst case. Over world 1's 17 places, the plain check flagged 4,078 of 12,032 objects; the triage kept 104 objects with real faults in 85 groups and marked the other 3,974 as false alarms, most of them kit pieces that stand where the kit lays them. The drop test ran on every place with loose pieces on its floor except the square, where it did not finish in three hours. The creator's pick of a model is written onto each of its objects as the file's hash, and an export that would show anything else for a picked row is refused unless the creator's decision to replace it is written down. Finally, each object is rendered alone from eight directions and compared with its close-up by its outline and by DINOv2 similarity [@oquab2023dinov2], and the least similar are listed first: in the lab, the four lowest were a mouse drawn black, a ceiling lamp without its lens, a scanner without its screen and a wall monitor with a blank screen. The collision queries behind these checks follow the interface of ProcFunc's scene tools [@raistrick2026procfunc], whose code is not yet released, built on python-fcl and trimesh, and one annotation step gives every check per-object masks, depth, normals and occlusion boundaries from any camera, the same labels a robotics world needs.

<!-- Gate, triage, picks, compare: tools/usd/complete.py, triage.py, collide.py, annotate.py, picks.py, compare.py; .claude/hooks/completion_guard.py (score 7ee78fc, 1ba8b74, ff44157, 1a1ce30). Counts: triage.py on world 1's exported stages of 2026-10-08/09, with settle.py drops (cloud) where loose floor pieces exist; per place in paper/evidence/agent-tools/triage/<place>.txt, summed in its summary.txt (12,032 objects, 4,078 flagged, 104 real). Lab compare: paper/evidence/agent-tools/lab-compare.json (likeness 0.28, 0.29, 0.34, 0.44). LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. -->

A place's people are part of its stage. Its cast records who is there, how many, where, doing what and why each is there, and nobody is placed who is not in it. Each person becomes a skinned character (UsdSkel) that plays a clip from its own starting point, in a layer of its own between the creator's edit layer and the base. A crowd is one point instancer of a cheap body, with a prototype for each clip, phase and palette of clothes. On the leader's walk, UsdSkel skins the converted body to within about a micrometre of the points the glTF file's own skinning gives. The prologue's square holds the leader on the podium, a front row of 24 people mixed from six kit builds, and a crowd of 10,000.

<!-- Characters: tools/characters (skel_usd.py, cast.py), data/characters/square.json; skinning agreement measured 2026-10-08 on the leader's walking clip, frame 20 (max 0.0013 mm); checked by tools/characters/characters_test.py. -->

Characters are made by the framework's character maker, which has one entry point. A short spec gives a name and a picture or a few words, and the maker returns a rigged, clothed, textured and animated character as a glTF file and as UsdSkel, with a far body for crowds and a set of clips. A person's whole chain runs on one rented card. The A-pose picture is the creator's own, or FLUX.2 klein 4B [@flux2klein] draws it from the words. SAM3DBody-cpp [@sam3dbodycpp], a C++ and ONNX runner of SAM 3D Body [@yang2026sam3dbody], reads the body off the picture, and the body is fitted to SOMA-X through MHR. Kimodo [@rempe2026kimodo] writes the clips from sentences. The clothes are GarmentCode's sewing patterns [@korosteleva2023garmentcode], draped on the body by the cloth solver of Newton [@newton], an open physics engine on NVIDIA Warp [@warp]. Hi3DGen [@ye2025hi3dgen] makes the hair from a clay picture of the bald head, and the hair is laid on the scalp as a shell. FLUX.2 klein base 4B [@flux2kleinbase] with a reference-depth LoRA [@refcontrol] draws the face on the head's own depth view. The chain then builds the character, converts it to UsdSkel and renders it for review. Rebuilt from her own picture, Nev, a crew member of the Moon base, took 11.2 minutes of an H100, and a new person made from one sentence took 21 minutes (Appendix G). Animals use the same entry point with a route that does not assume a human body: Pixal3D makes the mesh from a close-up, UniRig [@zhang2025unirig] rigs a quadruped, a fish gets a spine rig made in code, and the clips are made in code. Newton's drapes come close to those of GarmentCode's own solver, a fork of NVIDIA Warp that we cannot use because its licence allows non-commercial research only: on three bodies, the work suit's mean bend between neighbouring cloth triangles is 3.3 to 3.9 degrees, against 2.9 to 3.3 for Warp and 13.8 to 19.8 for Blender's cloth (Table G6). Every crew and cast body was draped again this way, and the cast writer refuses a body whose drapes come from a simulator that does not allow commercial use. Kimodo stands people 1.6 to 2.2 hip widths apart, so the build brings the feet in to hip width; the hands run up under the sleeves and the trouser legs into the boots, and a check measures the wrists, ankles and stance on every clip of every body. One part is weak: the animals' clips are made in code, so the dog's paws twist and its feet slide (Limitations).

<!-- Character maker: tools/characters/maker/make.py, spec.py, chain.py, data/characters/makes/<name>.json; the person chain on one card: tools/props/cloud/characters.py and characters_setup.sh; drapes: tools/characters/maker/garment.py, cloth_drape.py, drape_garment.py (score 91344d1, 440eb1c, bc566ca); hair: hair_mesh.py, hair_shell.py, hair_fit.py; face: drawings.py, face_depth.py, face_pick.py; animals: tools/characters/animals/route.py (score 657f6c9, 8d08e29, ee29b22). Nev's 11.2 min: the run's step minutes, listed in the comment under Table G4, and the ledger row of its batch in paper/evidence/cloud/ledger.jsonl. Warp fork licence: progress-characters-full.txt 12:56. Weak parts: handoffs characters-drape.txt and characters-animals.txt (2026-10-09). -->

A place's sound is also part of its stage, in its own layer. Every sound is a UsdMedia spatial audio prim with its file, its gain and how it plays. The place's room tones loop without a position. An object's own hum or fan loops where the object stands. Each library surface points at its footstep, impact and scrape sounds, which an engine plays when something happens on that surface. The levels, buses and reaches are those the game 2099 played, now kept as the framework's sound catalogue. On the hub, the layer holds 2 room tones, 23 object sounds and 9 surface sounds. The review's walk plays what its camera hears along its path: each sound at its gain over its distance from the eye, panned by where it stands across the view, and the demo's video tool mixes the same track into each shot. The world 1 videos of Appendix A were rendered before this layer existed and are silent.

<!-- Sound stage: tools/usd/sound.py, data/sound/catalogue.json and places.json (moved from 2099's sound catalogue and PlaceSounds), checked by tools/usd/sound_test.py; hub counts from a run on the hub's stage, 2026-10-09. -->

What moves in a place moves in its stage as well, in a layer of its own: OpenUSD time samples on the prims that the base already holds, at the game's own speeds and lengths. The airlock's doors sink 2.8 m into the floor at 3 m a second, and its warning light burns while the pump empties the chamber and while the tanks fill it again, five seconds each. The garage's big door slides apart at 2.5 m a second under a warning beacon, and the hangar's roof leaves slide 11.2 m at 3 m a second. How long a door stands open is the player's choice in the game, so the motion record sets those pauses itself and says so. In the launch view, the rocket lifts off 3 seconds after its engines light and climbs at the game's rocket thrust of 24 m/s² against Earth's gravity. The game never draws this, because the player rides the launch inside the capsule, so the climb is an addition of the record, timed by the game's launch sequence. Each motion also lists the sounds that the game plays with it and when, and the sound layer plays them from the moving prim. The places' vehicles and robots do not move yet: no place of world 1 shows the game's rover, drone or robots, and the street's car stands still in the game as well.

<!-- Motion stage: tools/usd/motion.py, data/motion/{airlock,garage,hangar,launch}.json, checked by tools/usd/motion_test.py (score 4a080da). Numbers: 2099 airlock.gd:13-17, airlock_cycle.gd:14-18 with pace.gd:19,39 (60 base minutes = 5 s); bay_room.gd:20-23,109-137 and bay_domain.gd:30-33 at 2099 dcb2954b; prologue.gd:76-80; mission_pilot.gd:17-19. -->

A place's particle effects are a stage layer as well, and each emitter is written twice. One prim carries the effect's parameters in the game's numbers: its emitter shape, rate, lifetime, speed, spread, gravity, size and opacity over its life, the wind it follows and its seed, so that an engine can make the effect again with its own particle system. Under it, the particles are baked as points over a loop that repeats exactly, so any USD reader shows them without knowing those parameters. The bake repeats the particle rules of Godot, the game's engine, with the framework's own seeded draws, so the same record always gives the same particles. The creator's rule for effects is to start from real footage and to use many fine particles, because big or sparse ones read as random dots, and the records keep the game's counts. On the calm afternoon that the camp's scene record holds, 30,000 grains of 3 cm blow along the ground on 25 cells round the camp, and two dust devils of 6,300 particles each wander downwind at 1.4 m/s; a storm variant of the same layer holds 180,630 particles. The flat holds the wisp and the breath of the cigarette smoked on its balcony, and the wreck the 40,000 grains that a supply rocket's engine throws across the landing pad. Seven of the game's ten kinds of emitter are placed. The dust thrown by a boot, a rover's wheel and a digger's scoop is not, because no place of world 1 holds the walker or the machine that throws it.

<!-- Effects stage: tools/usd/effects.py, data/effects/{camp,flat,wreck}.json, checked by tools/usd/effects_test.py (score 4fcd87e). Numbers: 2099 mars_wind.gd:18-52 (CELL_M 14, CELLS_OUT 2, 20,000 grains a cell at the calm share 0.06 = 1,200, DRIFT_GRAIN_M 0.03, 70 puffs a cell in a storm), dust_devil.gd:9-24 (6,000 grains and 300 veil cards), mars_wind.gd:56-61 (DEVIL_WANDER 1.4), supply_rocket_view.gd:333 (LANDING_GRAINS 40,000); the storm variant lays 3 x 3 cells (9 x 20,070). Ten kinds: drift grains, drift puffs, devil grains, devil veil, boot spray, wheel fan, scoop spill (DustThrow), landing dust, cigarette wisp and breath. -->

The framework stands apart from the game it was first built for. Every file a record names is in the repository or in one release of it: the first world's made models (199 MB packed) and its 121 sounds (36 MB), each listed with its checksum, its source and its licence. A check fails when any code or data names a file of the game's own tree.

Some surfaces need more than a flat library colour, so the framework writes its own shaders as UsdPreviewSurface materials over pictures it bakes. Any USD reader can draw these. One example is the Earth in the Moon's sky. Its continents, deserts, ice and cloud come from the game's own noise shader, ported to numpy and baked once into a longitude-latitude picture. The place's own sun lights the ball, so its night side falls dark. The sun's disc hangs along each place's sun as wide as the game draws it. The game's lamp, screen and grow-light materials are library surfaces.

<!-- Shaders: tools/usd/shaders.py, earth.py (port of 2099's ink_earth.gdshader), library variants warning_lamp, indicator_amber, grow_light, screen_teal, sun_disc in data/library/materials.json; checked by tools/usd/shaders_test.py and a Blender render of the wreck's Earth, 2026-10-09. -->

<!-- Separation: tools/assets/world.py, data/assets/world1.json (release world1-assets-1, 306 files), tools/assets/game_free_test.py (score 3b0ef7f). -->

::: gap
**Gap: the scene in a game engine.** The same stage loaded in a game engine, with its collision and surfaces, and the mass and friction of each object written into it. It waits on the game engine adapter and on the framework recording mass and friction.
:::

## Review tools

Each place ends with the creator's review. The review tools that SCORE supplies are pages that show each stage's output side by side, before-and-after shots from the same cameras, walkthroughs inside the engine, and the result of every check. An optional world step can turn the concept into a whole room that can be walked through, so that walls and objects the concept does not show can be seen; nothing it produces is shipped.

A review page is a static folder built only from the files the stages wrote, with the assembled scene rendered by Blender from the place's OpenUSD stage, on rented cards, from the cameras of its scene record and along a walk through it (Figure 8). Each view is laid beside the game's own shot from the same spot, and a view that is much darker than the game's fails a brightness check, which is how lamps whose light fell off too fast were found. A place with people shows each of them close and the crowd wide, and its walk is drawn at consecutive moments of the stage's time, so that the people move.

![The wreck's review page, from two runs of the route over the same place. (a) One model: its close-up, its labelled parts (one colour per library surface) and its baked model, each from the first run and the rerun, drawn from the same camera. (b) The assembled scene from one fixed camera, before and after the rerun. (c) The parts check for each take, with what it caught in the rerun: the split of seven takes did not register against their pictures, so each was painted whole.](figures/fig-review.jpg){width=100%}

<!-- Scene record views, game shots, brightness: tools/review/CLAUDE.md, page.py --game-shots (score f51d92b); the lamps: score 3a28fe7 (the rocket's floodlight, progress-complete-scenes.txt 00:00). Characters section: tools/review/characters.py (score 93df6a5). Page: tools/review/page.py wreck, runs place-outside/work/wreck (before) and the wreck's rerun from this repository (now, https://github.com/Babon-Innovations-b-v/score/issues/1#issuecomment-6060530977); "seven takes": that rerun's parts/*/labels.json, registration.registered false in 7 of the 13 splits, as the same comment reports. -->

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

## With and without the agent tools

The tools that check an agent's work (the completion gate, the resting triage with its drop test, the pick lock and the render-and-compare, Section 2) were tested on three places of world 1: a room (the workshop, 814 objects), an outdoor place (the street, 1,198 objects) and a dense room (the hangar, 1,657 objects). Each arm started from the same exported stage and the same inventory, and the same agent (Claude Opus 5.5 in Claude Code, headless) got the same prompt: make the place as complete as it can in about 50 minutes, through the place's layout data only. One arm had the framework as it was before these tools; the other had them. Both arms were measured afterwards with the same instruments (Table 2). Each arm ran once, so the table shows what happened, not an average.

**Table 2.** One session per arm and place. Faults are the resting triage's real faults left on the final stage, measured against the arm's own data; placeholders by the placeholder check; rows are inventory rows with no object and no written reason. Agent cost is the session's model cost in dollars; cloud is what its rented machines cost.

| Place, arm | Real faults (start → end) | Placeholders | Rows missing | Minutes | Agent cost | Output tokens | Cloud | Exports | Gate said unknown |
|---|---|---|---|---|---|---|---|---|---|
| Workshop, without | 18 → 13 | 0 → 0 | 1 → 0 | 36 | $2.26 | 30.4k | €0.85 | 7 | not used |
| Workshop, with | 18 → 0 | 0 → 0 | 1 → 0 | 26 | $1.42 | 14.3k | €0.85 | 2 | 2 of 4 calls |
| Street, without | 11 → 0 | 0 → 0 | 0 → 0 | 38 | $2.40 | 30.0k | €0.32 | 9 | not used |
| Street, with | 12 → 0 | 0 → 0 | 0 → 0 | 39 | $1.21 | 10.4k | €0.76 | 1 | 0 of 5 calls |
| Hangar, without | 14 → 4 | 5 → 0 | 0 → 0 | 47 | $2.01 | 26.6k | €0.00 | 7 | not used |
| Hangar, with | 14 → 9 | 5 → 0 | 0 → 0 | 32 | $2.34 | 29.1k | €0.64 | 5 | 3 of 6 calls |

The tools made building cheaper more often than they made the scene better. On the workshop and the street, the arm with the tools used about half the agent's output and cost, and exported the stage once or twice instead of seven to nine times, because the triage named the few real faults among hundreds of alarms. On the workshop it left no real fault, but 13 of its 18 were cleared by writing what holds a piece up into the inventory (the tools on the tool board hang from it; the arm monitors are clamped to their bench), which the creator still has to confirm; the other five were moved off the wall they stood in. On the hangar the arm without the tools left fewer faults: the arm with them spent its time replacing five placeholder slabs with the kit's own wall panels and ribs and trying the drop test, which failed on a room with no ground mesh (fixed after the run), and the nine faults it left are models with stray parts below their feet that no pose can fix. In no arm did the completion gate's hook have to refuse a claim, because no agent claimed a place was complete; both arms reported what was left. Every unknown answer of the gate was a check not yet run on the stage as it then was, which is what unknown means; the agents ran the checks and went on. Concept fit and the per-part surface check are not in the table, because their tools are not built yet, and no row carries an owner's pick, so the pick lock was never tested by an agent.

<!-- Benchmark: paper/evidence/agent-tools-bench: analysis.json (written by the bench's analyse.py from each session's record and transcript), and per arm and place (on = with, off = without) measure-start.json, measure-end.json, measure-manual.json and session.json. Arms: without = score 672ddfd, with = ff44157 (both with ff44157's data for the three places); claude -p --model claude-opus-5-5, 2026-10-09. The street's start reads 11 and 12 because the two start measures read the inventory from different checkouts; the stage was the same. The workshop's 13 cleared by data: 11 tool-board tools set to hanging, two arm monitors fixed (session report); 5 overlaps moved. -->

::: gap
**Gap: ablations.** This section will compare the framework with and without the optional world step, and with the checks before spending switched off, on the same places (the agent tools are compared above). It will measure how much of the concept is covered, how dense the built place is, the cost, the faults found after spending, and the creator's review. It waits until every stage runs from the framework repository.
:::

## Style coherence

Whether a place keeps one style is read from the review pages' renders of its generated models, which draw every model under the same light, against the same background and by the same camera rule, so that two renders differ only by the model. Three readings come from the pixels: how well the coloured pixels fit the place's palette, how much the models' lightness varies, and how blotchy their surfaces are, as the 75th percentile of the lightness spread within small tiles. A fourth comes from DINOv2 [@oquab2023dinov2]: how alike two models of one place are, against two models of different places, with the same pairs compared again as plain silhouettes and that difference subtracted, so that what an object is does not count as its style. Over world 1's 140 generated models in 16 places, DINOv2 finds models of one place more alike than models of different places, but almost all of that is shape: the silhouettes show nearly the same difference, and what is left for the look is 0.009 on the cosine scale, as a mean over models (95 percent bootstrap interval 0.003 to 0.015). Every place of world 1 draws on one surface library, so this reading shows how distinct the places are rather than how consistent each one is. The palette reading says almost nothing on renders: most models are greys, steels and dark panels, the places' palettes overlap almost entirely, and even the generator's own colours fit them.

The surface reading does respond to the method. On the 54 generated models of the garage, the hangar and the lab, each rendered once painted from the library and once with the colours of the picture it was generated from, the painted render was less blotchy for 43 of the 54 and more even from model to model, the difference that Figure 4b shows by eye. The two renders differ in geometry as well as paint, because the picture-coloured one is the generator's own mesh, so this does not isolate the paint (Appendix B). None of the readings has yet been checked against the creator's reviews: since its first room, the hub, which the creator accepted (Table C1), world 1 has not been reviewed, so there is nothing yet for a reading to separate, and the most weathered place, the old station, reads the most blotchy because its wear is intended. Until reviews of both kinds exist, these are measurements of renders, not a measure of style.

<!-- Tool: tools/review/style.py and its test style_test.py (score d859e5d, 7a8ec4b, 2ca5ba4, 453e06d). Input: world 1's review pages of 2026-10-09, 140 made-model renders (Blender Workbench, one studio light). DINOv2 facebook/dinov2-base (Apache-2.0) through tools/props/cloud/similar.py on rented L4 cards. Readings: paper/evidence/style/style.txt (140 models, 16 places; pooled gap 0.014 over 1,020 pairs within and 1,087 across, 11 pairs of copies left out; 34 of 140 models with enough coloured pixels, fit 1.000 except the greenhouse 0.992; coloured palettes shared 0.982) and paper/evidence/style/bootstrap.txt (per-model style gap 0.009 [0.003, 0.015] over 137 models; colour 0.073 and silhouettes 0.064 within less across). The picture's colours fit as well: paper/evidence/style/picture-coloured-style.txt. Paired: paper/evidence/style/paired.txt (painted less blotchy for 43 of 54, mean -1.09 L* [-1.50, -0.71]; spread over models 1.37 against 1.75). Reviews: Table C1 (the hub's round six) and Appendix B (world 1 not reviewed since its first room). Cloud: EUR 0.24, ledger rows similar-20261010-025514-908976, -030112-958530, -030718-1000812 and blender-20261010-030055-954867 in paper/evidence/cloud/ledger.jsonl. -->

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
- **Characters' clothes and animals' motion are rough.** Newton's drapes crumple a little more than Warp's: about 1 degree more between neighbouring cloth triangles on the 16 rebuilt bodies, and up to 7 degrees more at the space suit's waist on the broad builds. Most space suits are still moving slightly when the drape stops, and the work suit's trousers end 2 to 4 cm lower than Warp's. The animals' clips are made in code: the dog's paws twist, its sit reads as a crouch and its feet slide by up to 5.4 cm.

<!-- Drapes: handoffs/characters-drape.txt (hem 22.8 cm against Warp's 18.1 cm; crumples; space suit waist and sleeves). Animals: handoffs/characters-animals.txt (paws, sit, worst foot 5.4 cm from its goal on the walk). -->


# Future work

- Build the three further worlds: a stylised underwater world, a simulation world for robots, and a third-person fantasy world.
- Add a game engine adapter for the OpenUSD scene, and write each object's mass and friction into it.
- Make assets interactable, which robotics in particular needs.
- Finish the animals and the drapes: fins that move, animal motion retargeted from a captured set whose licence has been checked, and Newton's space suit brought fully to rest with less gathering at the waist.
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

## World 1: the game world of 2099

Figure A1 shows one frame of each of world 1's 17 places, in story order: the prologue on Earth, the Moon base and the ground around it, and the first camp on Mars. Every frame is rendered by Blender's Cycles from the place's OpenUSD stage, from one of the player's spots in its scene record, with the stage's own lights and sky and its characters; no game engine is involved. What a scene record lists as drawn only by the game, such as the ink outline pass, the haze and the stars, is missing. A walk-through video of every place was rendered the same way, two to four slow shots of 3.5 seconds a place from the player's spots, and joined in story order into one video of world 1, 3 minutes 35 seconds long, with each place's plain name on a title card. These videos were rendered before the stage had its sound, motion and effects layers, so they are silent and show none of them. For the videos, every surface map was reduced to at most 1,024 pixels. The creator has not yet reviewed world 1, so these pictures show the framework's output as it stands, not an accepted result.

![World 1 of SCORE, one frame of each of its 17 places in story order: the prologue on Earth (flat to launch view), the Moon base, its walkway tube and the ground around it (hub to old station), and the first camp on Mars. Rendered by Blender's Cycles from each place's OpenUSD stage, from one of the player's spots, with the stage's own lights, sky and characters; not reviewed by the creator. The habitat's and the flat's style texts came from the optional world step (Generated using World Labs).](figures/fig-world1.jpg){width=100%}

<!-- Frames: tools/review/demo.py plan/cut on world 1's exported stages (complete-scenes export, 2026-10-09 00:00, casts 01:32) copied with their maps at most 1024 px; frame per place in tmp/paper-demo/stills.json; figure by tmp/paper-demo/figures.py. Style texts from the world step: data/definitions/place.json lines 85 and 295 (marble/paint.json). Render: 34 cloud jobs, 5,292 frames at 1280x720, 64 samples, 20 L4 cards, 78.1 min, EUR 15.82 (paper/evidence/demo/world1-run.txt, last line; ledger batch blender-20261009-020545-2401425 in paper/evidence/cloud/ledger.jsonl). -->

The 17 places' videos were rendered as 5,292 frames at 1280 by 720 pixels, in 34 jobs spread over 20 rented L4 cards, in 78 minutes for €15.82.

Figure A2 follows two objects through the stages, from the concept to the place.

![Two objects through the stages: the lab's desk chair (top) and the wreck's forward section (bottom). From left: the concept the creator chose, the close-up drawn from it, the generated model with its parts, the model painted from the surface library, and the model in its place on the stage. The forward section shows a known fault: its scorched paint has no part of its own and is lost in painting (Section 5).](figures/fig-stages.jpg){width=100%}

<!-- Concepts: the picks lab C6 and wreck C2 (img/ of the lab and wreck review pages written by tools/review/page.py; the assembled figure is paper/figures/fig-stages.jpg); close-ups, parts and painted shots: the same pages' img/closeup-*.jpg and models/*--parts--now.png, *--made--now.png; placed: demo frames lab shot0-042, wreck shot1-000. -->

::: gap
**Gap: worlds 2 to 4, and a public link to the videos.** This appendix will show every place of the other three worlds in the same way. The videos of world 1 are not yet published at a public address.
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

<!-- Rows: data/inventory/<place>.json (flat and stairwell: prologue_flat.json, prologue_stairwell.json). Pieces and models: data/kit/<place>.json (pieces; models[*].route code or model), glow parts left out. Cloud: paper/evidence/cloud/ledger.jsonl rows from 2026-10-07T00:00Z, attributed by work folder and take name (bakes split per job entry, Pixal3D by job seconds, PartCrafter by folder; the hub's round six only, rows 219-236 and 239); unattributed sums the same way. Pictures and faults: playtest3/scaling-world1.tsv columns gemini_usd, faults_caught_before_spend, faults_after (lab rows 6 and 21 added: $2.68 + $1.47, faults 9/9 + 4/3); hub pictures progress-hub-r5.txt; the hub's faults are not tabulated in the tsv. Resting: the "Resting on the ground" tables of the places' review pages, 2026-10-08 17:05 to 23:25, copied to paper/evidence/world1/resting/<place>.txt; wreck and old station progress-usd.txt 23:27. The world's resting total over 12,066 pieces: the per-place counts summed (the old station's 29 objects include a child piece). -->

## Style readings

Table B2 gives the style readings for every place of world 1 with more than two generated models. The lightness spread is the standard deviation of the models' median lightness (L\*); over all 140 models it is 15.0. Marks is the median over the models of the 75th percentile of the L\* spread within tiles of 8 by 8 pixels on the model. Likeness is the mean DINOv2 class-token cosine of pairs within the place and across places, for the renders and for their silhouettes, and the gap is the renders' difference less the silhouettes'. The airlock, the launch view and the stairwell have one generated model each and the tube none; the habitat, the square and the street have two, too few to read.

**Table B2.** Style readings of world 1's generated models, per place.

| Place | Models | Lightness spread | Marks | Likeness within / across | Silhouettes within / across | Gap |
|---|---|---|---|---|---|---|
| Camp | 5 | 8.3 | 4.55 | 0.345 / 0.136 | 0.378 / 0.164 | −0.005 |
| Flat | 9 | 16.7 | 4.83 | 0.186 / 0.122 | 0.243 / 0.176 | −0.003 |
| Garage | 19 | 12.6 | 2.80 | 0.185 / 0.159 | 0.199 / 0.177 | 0.004 |
| Greenhouse | 3 | 4.5 | 6.12 | 0.071 / 0.140 | 0.140 / 0.174 | −0.035 |
| Hangar | 13 | 9.5 | 2.99 | 0.185 / 0.151 | 0.231 / 0.174 | −0.023 |
| Hub | 12 | 3.8 | 5.96 | 0.243 / 0.151 | 0.243 / 0.160 | 0.009 |
| Lab | 22 | 14.4 | 1.96 | 0.203 / 0.162 | 0.195 / 0.174 | 0.020 |
| Old station | 24 | 12.7 | 8.96 | 0.221 / 0.156 | 0.217 / 0.175 | 0.023 |
| Workshop | 8 | 3.8 | 7.28 | 0.402 / 0.158 | 0.400 / 0.178 | 0.022 |
| Wreck | 16 | 12.8 | 3.98 | 0.241 / 0.161 | 0.257 / 0.175 | −0.002 |

For the comparison with the pictures' own colours, each generated model of the garage, the hangar and the lab was rendered a second time as the take it came from, with the colours the picture model gave it. Painted from the library, the median marks fell from 2.99 to 2.80 in the garage, from 3.53 to 2.99 in the hangar and from 2.79 to 1.96 in the lab. The lightness spread rose, from 7.9, 6.4 and 8.7 to 12.6, 9.5 and 14.4, because the library gives a place dark and light panels on purpose while the generator's colours stay in the middle tones. The DINOv2 gap read 0.007 painted against 0.000 with the picture's colours, a difference for which no interval was computed. The take is the generator's own mesh, at its own pose and density, while the made model is rebuilt from its parts, so the difference in marks mixes the paint with the geometry. The workshop's models are the hub's tools, reused under the rule against duplicates; any two renders of one model, in two places or within one, are left out of the likeness, which would otherwise count one model as two that agree.

<!-- Table B2: paper/evidence/style/style.txt (world 1, 2026-10-10), places with three models or more. Paired numbers: paper/evidence/style/paired.txt, painted-style.txt and picture-coloured-style.txt; the takes are the Pixal3D takes named by each made model's labels.json, rendered by tools/blender/inside/review_models.py on 3 rented L4 cards (EUR 0.12, ledger row blender-20261010-030055-954867). Copies left out: 11 pairs, listed in style.txt. -->

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
- **Resting triage:** each object's support comes from its inventory row: a glowing part or screen is judged with its host; a fixed row stands as laid but may not float unless joined to another piece; a kit's shell pieces stand in the kit's frame; a hanging row and a wall or ceiling row need one contact with anything; a floor row and a row standing on another need four points of their footing (the points within 10 cm of their lowest) within 3 cm of a surface under them, with their weight within 5 cm of the area those points span. An overlap deeper than 3 cm counts only if the two still meet after the loose one moves 5 mm away. Cables may sink 6 cm, cloths 8 cm and ground debris 30 cm. From a drop run, an object that moves more than 0.2 m or turns more than 8 degrees is a real fault.
- **Completion gate:** the requirements given in Section 2 under the canonical scene, each with its result tied to a fingerprint of the stage's files and inputs; a result made on another stage counts as unknown.
- **Pick lock and render-and-compare:** a picked row's objects must show the model with the picked hash, or the row must carry the creator's written replacement. Each object with a close-up is rendered from eight directions 20 degrees up, and the direction with the highest DINOv2 likeness stands for the close-up's camera; the outline score is the overlap of the two silhouettes, each cut to its box.
- **Brightness check:** each view of a place's stage on its review page is shown beside the game's shot from the same spot, and a view whose mean brightness is under half the game's fails.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). Close-up check: tools/props/closeup/check.py. Settling and resting: tools/usd/CLAUDE.md, settle.py, resting.py (15 degrees, 30 cm; debris 1.4 m, 1 m). Brightness: tools/review/CLAUDE.md (a scene view under half the game's). -->

# Models and licences

Every model in the framework must allow commercial use of its output (Table E1). Candidate models were dropped under this rule; among them were NVIDIA's Lyra 2.0, whose weights are licensed for internal research only, and Hunyuan3D 2.1, whose licence does not apply in the European Union. We read each licence for its clauses on commercial use. Four of the models read pictures through Meta's DINO family of models, each through its own copy. What passes from one model to the next is always pictures, masks, depth maps or meshes, never one model's internal features. The characters' licence check found that GarmentCode's fork of NVIDIA Warp, which drapes its patterns, allows non-commercial research only, so Newton's cloth solver on upstream Warp, both Apache-2.0, replaced it; Blender's cloth simulation [@blender] is kept as a second route. The one open doubt among the characters' models is the face LoRA, whose training data is not disclosed.

**Table E1.** Models in the framework.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups the open model fails, ground skins | paid API |
| Qwen-Image-Edit-2511 [@qwenimageedit] | close-ups, first | Apache-2.0 |
| Qwen3.8-27B [@qwen38] | the close-ups' shape check; each part's material | Apache-2.0 |
| Pixal3D [@li2026pixal3d] | picture to 3D | MIT; DINOv3 licence [@simeoni2025dinov3] for its encoder |
| PartCrafter [@lin2025partcrafter] | parts | MIT; its non-commercial background remover not used |
| SegviGen [@li2026segvigen] | parts of our own model (trial) | MIT, on TRELLIS.2 (MIT); DINOv3 licence for its encoder; its non-commercial background remover and nvdiffrast not used |
| GeoSAM2 [@deng2025geosam2] | parts of our own model, seeded by the close-up's regions (trial) | Apache-2.0 |
| Depth Anything V2 Small [@yang2024dav2] | ground relief | Apache-2.0 |
| ProcFunc, Infinigen shaders | surfaces | BSD-3-Clause |
| MOSS-SoundEffect v2.0, CLAP | sound | Apache-2.0 |
| World Labs Marble [@marble_terms] | optional world step | paid; outputs owned by paid users |
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
| MakeHuman eyes | the characters' eyes | CC0 |

On our tier, Nano Banana Pro allows 250 pictures a day and 20 a minute; the cheaper Nano Banana (gemini-2.5-flash-image) allows 2,000 a day and 500 a minute. We tested whether the cheaper model could draw the close-ups instead, on the same 10 lab objects with the same prompts and inputs (Table E2). It refused the standard prompt for 6 of the 10 objects and drew those only from the crop alone, and its pictures were about one megapixel with the object small in the frame. Close-ups therefore stay on Nano Banana Pro.

**Table E2.** Ten lab close-ups drawn by Nano Banana instead of Nano Banana Pro.

| Result | Objects |
|---|---|
| good | 2 |
| usable | 3 |
| marginal | 1 |
| wrong shape (microscope, chair, sample tray) | 3 |
| refused (glovebox) | 1 |

<!-- Tier limits and the 10-pair check: the coordinator's brief, lines PICTURE MODELS and CLOSE-UP CHECK RESULT (2026-10-08), copied to paper/evidence/pictures/closeup-check.txt; the check's side-by-side page was private and is not published. -->

The close-ups' shape check was tuned on 40 close-ups that four open picture models drew of the lab's ten objects, each scored by hand as good, usable, marginal, wrong or failed, and on Nano Banana Pro's ten pictures of the same objects. With the majority of three sampled answers, the check agreed with the hand score on 29 of the 40, passed all ten of the closed model's pictures and two marginal ones, passed none of the pictures scored wrong or failed, and failed nine that were good or usable, each of which then cost a picture from the closed model. The judge's single answer at temperature zero was rejected: asked the same 51 questions twice in one batch, it gave a different verdict on 7 of them. On the lab's 22 generated rows, an earlier version of the check accepted 8 of the open model's close-ups and sent 14 to the closed model; 7 of the closed model's first pictures failed for drawing the room or dimension lines around the object, and all 7 passed when redrawn from the crop alone. On the 17 rows that world 1 still needed afterwards, from three places, none of the open model's pictures passed; the closed model's pictures were accepted for 10 rows, and 7 rows were left for the creator to look at.

**Table E3.** The close-up stage on world 1. Cloud is rented card time in euros; the closed model's pictures are in dollars.

| Run | Close-ups | Open model accepted | Closed model accepted | Left for the creator | Cloud | Closed model |
|---|---|---|---|---|---|---|
| Lab, 22 rows (earlier check: one answer) | 22 | 8 | 14 | 0 | €4.12 | $2.81 |
| World 1's remaining rows (three places) | 17 | 0 | 10 | 7 | €3.06 | $4.02 |

<!-- Tuning: progress-openpics.txt 18:53 (vote: 29/40 agree, 0 wrong/failed passed, 2 marginal passed, 9 wrong fails; Pro 10/10), greedy rejected 17:56 (7/51 differed). Lab: progress-openpics.txt 17:35 (8 Qwen, 14 Pro, 7 Pro first takes failed for the room or dimension lines, all crop-only retakes passed, EUR 4.12 cloud, $2.81 Pro). World 1: progress-world1-score.txt 18:55 (workshop, greenhouse, campgrounds; 17 rows) and 20:12 (10/17 accepted, all by Pro, Qwen 0/17, 7 for review, EUR 3.06, Pro $4.02). -->

The picture-to-3D step, the part splitting, the surface bakes, the sound generation, all checks and the assembly run automatically. Coding agents (Claude Code [@claudecode]) write the plans, the inventories and every code builder; in the hub's final round, 86 of its 98 models were built in code. Some steps were still done by hand: some generated objects were turned to face the right way by eye, and a few labels were placed by hand before a rule took over that job. The concepts and the verdicts are the creator's own choices.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. Characters' licences: the characters' licence check of job characters-full, 2026-10-09 (progress-characters-full.txt 12:56, the coordinator's brief to the paper agent), recorded in tools/props/cloud/characters_setup.sh and tools/characters/maker/CLAUDE.md; Hugging Face licence tags of FLUX.2-klein-base-4B, refcontrol-FLUX.2-klein-4B-reference-depth-lora (apache-2.0) and VAST-AI/UniRig (mit), read 2026-10-09; SAM3DBody-cpp LICENSE (MIT). -->

# Surfaces, sound and light

The surface library holds families of variants: painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light and print. After the hub's second round it held 71 variants made from 14 ProcFunc recipes. Each variant is a recipe with settings, takes its colours only from the palette, and is baked into base-colour, metal-roughness and normal maps at a texture density that depends on how close the player can get. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor that a piece stands on. Every sound starts from a short written brief about its object. Four takes are generated for each sound, scored by how well CLAP matches them to their prompt minus any measured faults (clipping, unsteady loops or bad joins), and levelled to one loudness per kind of sound under a true peak of -3 dBTP. A creator may swap any take. For the game 2099, all 61 sounds were generated as 244 takes in one batch for €1.61, and the creator chose to keep earlier recordings for three kinds of sound: breathing, a sliding door, and footsteps on steel.

<!-- 71/14: progress-robust-exp.txt round two. Kick wear 32 cm: 2099 docs/bible.md item 11. Sound: 2099 docs/bible.md item 12; 2099 paper writing/status.md, seventh pass. -->

Light adds up, so it is planned as layers. For each kind of module, the bounce light of each group of lamps, and of a few sun directions through the windows, will be baked on rented machines as a separate layer, and the engine will mix these layers live according to each lamp's brightness. Outdoor light and the light on moving objects stay live. This part is not built yet.

<!-- Light layers: the owner's plan of 2026-10-06, not built and not yet written down in the repository; the paragraph carries no number. -->

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

Table G3 sums the cloud ledger, in which every runner records each machine it rents, by type of machine, from the first batch on 29 September to the end of 8 October 2026. It holds the game 2099's own test and benchmark machines as well as the framework's batches. €35.68 has no type: the machines of the earliest batches were recorded without one (€34.69), and some rows hold €0.99 more than the machines they list.

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
| type not recorded | | | €35.68 |
| total | | | €366.76 |

<!-- paper/evidence/cloud/ledger.jsonl, its first 746 rows (those written by the end of 8 October, all started before 2026-10-08T22:00Z, midnight CEST, from 2026-09-29T10:07Z); machines[].type, minutes, euros summed; rows without machines[] (EUR 34.69) and the euros of rows beyond their machines (EUR 0.99) summed as "type not recorded": python3 tools/costs/costs.py types paper/evidence/cloud/ledger.jsonl 746 2026-10-08T22:00Z. Types: L4-1-24G, H100-1-80G, H100-SXM-2-80G, POP2-32C-128G, L4-2-24G, POP2-16C-64G, POP2-HC-32C-64G, L40S-1-48G, RENDER-S, POP2-HM-16C-128G. -->

The character maker runs a person's whole chain on one card (Table G4). Its machine is set up once with six environments side by side, after the CUDA 12.6 toolkit that SAM3DBody-cpp needs: 11.0 minutes on an H100 and 21 to 25 minutes on an L4. On an H100, SAM3DBody-cpp's network takes 1.3 s and its whole call about 4 s once warm, 44 s cold. Against the Python SAM 3D Body on the same picture, its shape parameters correlate at 0.98, and its body at rest is 23 mm shorter (1.548 m against 1.571 m), with a mean gap of 17.6 mm between vertices and joints 19 mm apart on average and 25 mm at worst. The difference comes from the person box: SAM3DBody-cpp finds its own with YOLO, while the Python run was given the whole picture. Kimodo with its text encoder on the same card writes a clip in 30 s once warm, and the first in 82 s, which includes downloading the Llama 3 encoder. Nev's 19 clips had been made already, so her rebuild wrote none. On her walk, the built character's skinning, with 27 joints and thinned weights as an engine plays it, keeps within 6.8 mm of the body model's own posed points on average and 52.6 mm at worst (4.9 mm on average off the hands), and its file is 5.05 MB. Her far body has 612 vertices and 1,220 triangles, her work suit 31,260 triangles and her space suit 44,846. The development machine on which the chain was built and Nev was rebuilt ran for 163 billed minutes and cost €7.79 in all. On an L4, the same chain made the player from the creator's drawing of him, on his own body 1.742 m tall, in 26.2 minutes, for about €0.35 of the card at €0.79 an hour. The face is the slow step on an L4: klein base 4B with the LoRA, 50 steps and two seeds, took 13.6 of those minutes against 2.7 on the H100. The L4 was set up in 24.8 minutes. A new person made from words alone, an engineer, first reached the build on a second L4 and failed at the arm stripe of her space suit, because the drape had left her upper arm bare; the drape now tries again when a sleeve does not cover the upper arm. The batch of both people cost €1.50 for 60 minutes on three L4 machines, one of which failed its setup after 25 minutes because Kimodo's C++ extension was built while the CUDA toolkit installed beside it; the toolkit now installs first. Made again on an H100, the engineer took 20.9 minutes: klein drew her picture in 0.27 minutes, the drapes took 6.65 and the review renders 5.96, because a fresh H100 first compiles Cycles' kernels. On a 16-core processor machine, Blender drapes the work suit in 1.5 minutes and the space suit in 0.6 minutes, with every seam within 3 cm and no cloth inside the body. Newton drapes a garment in 2 to 4 minutes on an L4 (Table G6). Draping the 16 crew and cast bodies again with Newton and building them cost €19.31 on L4 machines over three rounds; the first took 12 machines for 64 minutes and €7.38, and the other two mended the trousers' waist hold and the boots.

The animals' route rents cheaper cards. One Pixal3D run on an L40S made both animals' meshes in 11.2 minutes for €0.29, and UniRig rigs a model in about 70 s on an L4. The rig, the clips, the far levels and the review renders take 5.2 minutes of an L4 for €0.08. A processor machine costs 10 to 15 times more for the same job: the fish's own Blender run went to a 32-core processor machine when no card was free and cost €0.85. UsdSkel skins the animals to within 0.2 µm of their glTF skinning for the dog and 0.01 µm for the fish. The fish's levels have 40,000, 6,000 and 532 triangles, the dog's 39,999, 5,999 and 1,500.

**Table G4.** Characters made by the character maker, 9 October 2026. Minutes of card time per group of steps; a person's cost is the card time of the chain alone, without the setup; the fish and the dog shared one Pixal3D run on an L40S, split evenly here, and their costs are on cards for every step.

| Character | Card | Picture | Body or mesh | Rig and clips | Clothes | Head, hair and face | Build and review | Total | Cost | Setup |
|---|---|---|---|---|---|---|---|---|---|---|
| Nev, from her picture | H100 PCIe | 0 (her own) | 0.13 | 0 (made already) | 4.75 | 4.23 | 2.09 | 11.2 min | €0.54 | not measured cleanly |
| The engineer, from words | H100 PCIe | 0.27 | 0.91 | 0 (made already) | 6.65 | 5.21 | 7.84 | 20.9 min | €1.00 | 11.0 min |
| The player, from the creator's drawing | L4 | 0 (the creator's drawing) | 0.34 | 0 (made already) | 5.18 | 17.08 | 3.60 | 26.2 min | €0.35 | 24.8 min |
| Dog, from words | L4; L40S for the mesh | 2 (4 pictures) | 5.6 | about 1.2 (UniRig) | | | 5.2 | about 14 min | about €0.40 | about 1.5 min (UniRig) |
| Fish, from a close-up | L40S for the mesh; L4 | 0 (given) | 5.6 | in code | | | on an L4 as the dog's | | about €0.32 | |

<!-- The make.json and nev_rebuild.json files named here were overwritten by later rebuilds; their values are kept as read on 2026-10-09, and every euro figure is a row of paper/evidence/cloud/ledger.jsonl. Nev: its make.json (fresh run on one H100 PCIe, 2026-10-09: picture 0, body 0.07, rest 0.06, clips 0 "every clip was made already", drapes 4.75, head 0.01, hair 1.51, face 2.71, build 1.59, review 0.5; total 11.2). Euros: the ledger row of batch characters-20261009-125955-2787986 (H100-1-80G, EUR 7.787325 for 163 billed minutes, EUR 2.87 an hour; 11.2 min x 2.87 / 60 = EUR 0.54). Setup: Nev's machine was mended by hand during its setup, so it has no clean figure; the engineer's H100 set up in 11.0 min (run characters-20261009-165908-3576550; progress-characters-full.txt 17:12), the L4s in 24.8 and 21.1 min (run characters-20261009-153040-3208249). Engineer: its make.json (NVIDIA H100 PCIe: picture 0.27, body 0.73, rest 0.18, clips 0, drapes 6.65, head 0.01, hair 1.58, face 3.62, build 1.88, review 5.96; total 20.88); 20.88 x 2.87 / 60 = EUR 1.00; the run's ledger row EUR 1.77 for 36.1 min. Cold Cycles kernels on an H100: score 0b87e56 (218 s cold). SAM3DBody-cpp and Kimodo timings, the comparison with Python SAM 3D Body (shape correlation 0.98, 1.548 against 1.571 m, 17.6 mm mean vertex gap, joints 19.0 mm mean and 25.4 mm worst, warm call about 4 s): progress-characters-full.txt 13:27 and 16:06. Player: its make.json (NVIDIA L4: picture 0, body 0.09, rest 0.25, clips 0, drapes 5.18, head 0.01, hair 3.47, face 13.6, build 2.32, review 1.28; total 26.2); height 1.742 m, face 50 steps and two seeds: the coordinator's message, 2026-10-09; ledger row characters-20261009-153040-3208249 (the player's L4 52.1 min, EUR 0.695625 billed at EUR 0.79 an hour; 26.2 x 0.79 / 60 = EUR 0.35); L4 setup 24.8 min: progress-characters-full.txt 16:06; batch total and the failed setup: the batch's run log, lines 25 and 37 (paper/evidence/characters/characters-run2-lines.txt) ("characters: 60 min on 3 machines, EUR 1.50"), progress-characters-full.txt 16:06; engineer_ama: its make.json (picture by klein, drapes 7.35, hair 3.21, the next step failed) and chain.log; the arm-stripe cause: the coordinator's message.  Build: nev_rebuild.json (joints 27; skinningGapMillimetres, measured by tools/characters/people/body.py on the walking clip against SOMA-X's own posing, mean 6.78, worst 52.56, meanOffTheHands 4.86; bytes 5,051,068; levels far 612 vertices, 1,220 triangles; work 31,260; suit 44,846). Drapes: handoffs/characters-drape.txt (POP2-16C-64G, work suit 1.5 min, space suit 0.6 min; seams within 3 cm, 0 points inside the body). Animals: handoffs/characters-animals.txt (dog picture: klein, 4 pictures, L4, 2 min, EUR 0.03; Pixal3D one L40S 11.2 min both, EUR 0.29, plus an H100 that never started, EUR 0.19, so EUR 0.24 an animal; UniRig on an L4 25-33 s skeleton, 27-28 s skin, 9 s merge, setup about 1.5 min; rig, clips, LODs and review on an L4 5.2 min EUR 0.08 for the dog; the fish's on POP2-HC-32C-64G 4.0 min EUR 0.85, POP2-32C-128G 4.9 min EUR 1.18; per animal on cards: fish about EUR 0.32, dog about EUR 0.40; UsdSkel 0.2 um dog walk, 0.01 um fish swim; LODs fish 40000/6000/532, dog 39999/5999/1500). Dog total: 2 + 5.6 + 1.2 + 5.2 = 14.0 min. -->

Since 9 October every stage that loads a model also runs from a pinned container image, one image per kind of job, built from files in the repository and pushed to a private registry chosen through the provider interface. The weights are not in the images: a job fetches each model once per node from our own object storage into a cache on the node, checked by its hash, and the first node to need a model seeds the storage from its pinned source. Each model's licence is recorded beside its image. Table G5 compares the time from a machine answering to the start of work under the old route, in which a fresh machine installed its software and downloaded its weights itself, with the image route on a new node. The old route was already fast for the kinds whose software comes as prebuilt packages, so the images gained little there and were slower for the largest weights, which come from our storage more slowly than from Hugging Face. They gained where the old route compiled or built: the part splitters, the character chain, and the first Cycles render on an H100, which compiled its kernels for 218 s because Blender ships no binary for that card and now reads them from a cache kept per card and driver. On a warm node an image's weights are ready in under a second.

**Table G5.** Cold start per kind of job, 9 October 2026: from the machine answering to the start of work. The old route installs and downloads on a fresh machine; the image route pulls the image and reads the weights from our storage on a new node.

| Job | Card | Old route | Image route (pull + weights) |
|---|---|---|---|
| Pixal3D | L4 | 1.5 min | 1.2 min (13 s + 58 s, 9.2 GB) |
| PartCrafter | L4 | 1.0 min | 1.0 min (47 s + 14 s, 4.0 GB) |
| GeoSAM2 and SegviGen | H100 | 5.2 min | 4.0 min (111 s + 128 s, 23 GB) |
| shape-check judge, Qwen3.8-27B | H100 | 1.0 to 1.5 min | 3.5 min (62 s + 146 s, 31 GB) |
| Qwen-Image-Edit | H100 | 1.0 min | 4.4 min (30 s + 231 s, 58 GB) |
| FLUX.2 klein | L4 | 0.8 min | 1.8 min (37 s + 68 s) |
| SAM 3 cut-outs | L4 | 0.9 min | 1.2 min (57 s + 13 s) |
| MOSS sound | L4 | not measured | 1.8 min (61 s + 44 s) |
| character chain (six environments) | L4 | 24.8 min | motion and body steps 2.7 min (72 s + 90 s) |
| first Cycles render | H100 | 218 s | 0.3 s, kernels from the cache |

<!-- Old route: setup medians from the machine answering to the end of setup in the runners' run folders (setup.log and known_hosts times), as reported by the image agents in tmp/playtest3/progress-cloud-k8s.txt (19:02 and 19:13 lines); judge checked by hand on run judge-20261009-183912-4001666 (18:39:52 to 18:41:22: its known_hosts and setup.log file times, paper/evidence/cloud/judge-times.txt; 30 GB fetched in 57 s: setup.log line 4, paper/evidence/cloud/judge-setup.txt); character chain 24.8 min: run characters-20261009-153040 (see Table G4's note). Image route: tools/cloud/images/images.json proof entries (pull_seconds, weights_seconds per kind; score 2ad1360, 68376a0, 86aede5) and the images-3d results in tmp/images-3d/results-*.json; character steps: the motion image's proof (pull 71.6 s, Kimodo weights 90 s). Cycles: images.json blender first_render, score 0b87e56 (218 to 220 s cold, 0.32 s with the 33 MB cache sm90-<driver>). -->

The same images run on any Kubernetes cluster. A job becomes one Kubernetes Job, allowed on its kind's classes in the order of Table G1's rules, on node pools per class that scale from zero with the cluster's autoscaler; when no pool of those classes can get a node, the job is widened to the next class and keeps the ones it had, so it never settles for one card. A job writes its result last and is skipped when that result exists, so a run resumes after a lost node. On Scaleway's managed clusters, whose control plane is free, an L4 node went from the order to a running job in 249 to 326 s in five runs: the node was ready after about 140 s and NVIDIA's driver setup took about 2.5 minutes more, against a rented machine that answers in 0.5 to 1.5 minutes. One job alone therefore finishes later on a cold cluster (a PartCrafter split took 8.1 minutes against 4.6 and cost €0.20 against €0.07, with identical output), while a job on a warm node starts in about a second. When an L4 zone was out of stock the autoscaler moved to the next zone within a minute, and when processor machines were out of stock in both Paris zones for 20 minutes, a cluster spanning Warsaw took one there.

<!-- k8s agent reports in tmp/playtest3/progress-cloud-k8s.txt (16:19, 16:48, 16:54 and later lines); tools/cloud/k8s/CLAUDE.md and clusters/scaleway.py docstring; parts proof (identical object.glb and 4 parts, 8.1 min EUR 0.20 against 4.6 min EUR 0.07): k8s agent report after eaffb37; renders and bakes on the cluster (report.json identical, pictures within 1/255 to 32/255 on 0.01 % of pixels): score 7c7c827, 4f8eb41. -->

**Table G6.** Drapes of the same GarmentCode patterns on the same three bodies by three simulators, 9 October 2026, measured by tools/characters/maker/drape_measure.py: the trousers' hem above the floor, the mean bend between neighbouring cloth triangles over the whole garment (crumple) and between the hips and the lowest ribs (waist), and the height of the space suit's belt band that the torso cloth covers. Warp is GarmentCode's own fork, run as a reference only; Newton is the route the framework uses.

| Body and garment | Warp: hem, crumple, waist, belt | Blender's cloth | Newton |
|---|---|---|---|
| Nev, work suit | 18.1 cm, 3.28°, 3.69°, – | 22.0 cm, 19.8°, 23.8°, – | 16.8 cm, 3.91°, 3.69°, – |
| Nev, space suit | 18.8 cm, 5.89°, 6.53°, 1.70 cm | 22.6 cm, 19.9°, 24.6°, 2.65 cm | 17.8 cm, 6.59°, 7.15°, 2.95 cm |
| The engineer, work suit | 19.6 cm, 3.10°, 3.62°, – | 23.9 cm, 17.8°, 24.8°, – | 17.3 cm, 3.54°, 3.52°, – |
| The engineer, space suit | 20.1 cm, 5.66°, 6.36°, 2.19 cm | 24.0 cm, 18.1°, 21.4°, 3.08 cm | 20.4 cm, 6.08°, 6.76°, 3.03 cm |
| The player, work suit | 18.6 cm, 2.87°, 3.06°, – | 23.2 cm, 13.8°, 15.2°, – | 16.9 cm, 3.33°, 2.95°, – |
| The player, space suit | 19.7 cm, 5.10°, 5.52°, 0.11 cm | 21.5 cm, 17.9°, 20.7°, 4.17 cm | 19.1 cm, 5.87°, 6.65°, 0.32 cm |

<!-- drapes job, 2026-10-09: the drapes-sim agent's final report (score f10dc5f, tools/characters/maker/newton_drape.py, Newton 1.6.1 SolverVBD on Warp 1.18.0; one L4, 98 min, EUR 1.30); the drapes are in that job's run folders, not published (the Warp reference reproduced Nev's kept drape: hem 18.16, crumple 3.284, inside the Warp range of 2.9 to 3.3 degrees in f10dc5f's message); Blender 4.2.23 on the characters box. Rebuild of the 16 bodies: paper/evidence/characters/rebuild-summary.json; costs from the ledger rows of batches characters-20261009-193220-31593, EUR 7.38 (12 L4, 64 min), -204559-166038 and -214931-281304, 4.55 + 0.68 (trousers and kit_w_broad reruns), and -232049-340705 with -224432-321196, 6.21 + 0.49 = 6.70 (round 3: boots and trousers waist), total 19.31 without the 0.51 Blender proof. Stance 1.6 to 2.2 hip widths in Kimodo's clips: the hands agent's report (standing 2.14 in the npz); joins.py on old and new bodies: the joins of each body in paper/evidence/characters/rebuild-summary.json. -->


Table G7 shows how a batch's time falls with the number of cards on the cluster. The same 24 Pixal3D takes, three at once on each L4, were run on one, two, four and eight nodes side by side. Every run used about the same card time, 210 to 221 minutes, and so cost about the same, while the time to the last result fell from 217 to 48 minutes. The four- and eight-node runs fell short of a linear speed-up for two reasons: only one zone had L4 cards, so their last nodes came 23 and 27 minutes after the order while the autoscaler kept retrying the other two zones, and eight nodes ran only eight jobs, so the run ended with its slowest job of 38 minutes.

**Table G7.** One batch on more cards: 24 Pixal3D takes, three at once on each L4, on a Scaleway cluster spanning Paris and Warsaw, 9 October 2026. Time runs from the submit to the last result; card time is the minutes the run's jobs held a card.

| Nodes | Time | Speed-up | Last node came | Card time | Cost of card time |
|---|---|---|---|---|---|
| 1 | 216.7 min | 1.0 | after 4.6 min | 210 min | €2.76 |
| 2 | 118.9 min | 1.8 | after 4.2 min | 215 min | €2.82 |
| 4 | 83.6 min | 2.6 | after 27 min | 214 min | €2.81 |
| 8 | 48.0 min | 4.5 | after 23 min | 221 min | €2.90 |

<!-- k8s agent's final report and tmp/playtest3/progress-cloud-k8s.txt (scale test lines): cluster score-jobs-kosmos, runs scale.py 1/2/4/8 (pixal runs 20261009-1750xx and 1751xx), wreck rows x seeds 1-3, names <row>-scale<N>-s<seed>, 96 of 96 takes made; work per job 20 to 38 min; 12 L4 nodes came, all in fr-par-2, 28 orders to fr-par-1 and pl-waw-2 out of stock; all scale-test nodes EUR 13.27 for 1011 node minutes, of which EUR 11.29 card time (the rest idle tails and cold boots). The uploads from the PC (13 min, four runs at once) and the bringing back of outputs are outside the times. -->

Tables G8 to G11 give the cost and time of October 2026 up to the provider's bill read on 10 October at 01:36 UTC. "Per stage" means here per kind of batch. The ledger records each batch's kind, its machines, their minutes and their price, but not the world, the place or the stage of a place's route that the batch served, so neither the cost of a world nor the cost of each stage of a place's route is recorded yet; only world 1 has been built, and Appendix B attributes its batches to places by their work folders. The tables cover October only, because the bill is read per month.

Up to the read, the ledger holds €547.31 of the bill's €627.74. Of the €80.43 between them, €51.87 is not compute: block storage for the machines' disks and one kept snapshot (€32.77), public IP addresses (€15.09), the image registry and the cluster control plane (€3.50), and object storage and secrets (€0.51). The other €28.56 is compute, and Table G11 traces it. €26.01 is processor machines that the ledger priced by the minute while the provider bills them by the started hour, almost all in rows written before the runner began pricing them by the hour on 8 October; €0.24 is two small machines that no batch rented; and the remaining €2.31 is the card types' bill and ledger differing by a few euros either way, because the bill lags the ledger by some hours. The ledger's rows are never rewritten: a reconciliation file kept beside it tags as Pixal3D the 55 October rows (€91.68) written before that runner named its kind.

Table G8 adds the €80.43 to each kind of batch in proportion to its share of the ledger, since disks and addresses come with every machine and scale with its rented time; this is an allocation, not a measurement. Blender work and Pixal3D were about half of the month's spend, and the open judge a tenth. By what the work was for, €112.41 of the ledger was research and development on the framework itself: the game's engine runs, the container images and their proofs, the method experiments, and the benchmarks and comparisons that the rows name as such, among them the scale test of Table G7. The other €434.90 was production, the route's work on world 1. Production is an upper bound, because the route's own batches carry no mark when they were reruns made while the method changed, such as the hub's six rounds (Table C1).

**Table G8.** Cost and time per kind of batch, 1 to 10 October 2026. Batches and machine time from the cloud ledger; the column "with the rest of the bill" adds the €80.43 that the ledger does not hold in proportion to each kind's share. The median batch is the median wall time of the kind's batches.

| Kind of batch | Batches | Machine time | Ledger | Share | With the rest of the bill | Median batch | Main card types |
|---|---|---|---|---|---|---|---|
| Blender: settling, renders, review pages, close-ups | 299 | 140.9 h | €155.42 | 28.4% | €178.26 | 12 min | L4 52%, 16-core processor 14% |
| Pixal3D models | 83 | 154.2 h | €130.98 | 23.9% | €150.23 | 40 min | L4 93%, H100 PCIe 3% |
| Open judge | 82 | 16.1 h | €55.75 | 10.2% | €63.95 | 11 min | H100 PCIe 55%, two H100 SXM 37% |
| Library bake | 238 | 50.7 h | €46.30 | 8.5% | €53.11 | 8 min | L4 84%, 16-core processor 8% |
| Characters: chain, rigging, drapes | 16 | 35.3 h | €35.31 | 6.5% | €40.50 | 45 min | L4 72%, H100 PCIe 28% |
| Parts and segments | 119 | 26.3 h | €33.27 | 6.1% | €38.16 | 8 min | L4 53%, H100 PCIe 35% |
| Engine runs: tests, shots, benchmarks, warm pool | 142 | 39.3 h | €32.63 | 6.0% | €37.42 | 9 min | L4 70%, 32-core processor, 64 GB 30%, read from their price |
| Container images, proofs, kernel warm-up | 48 | 10.8 h | €24.06 | 4.4% | €27.60 | 10 min | 16-core processor 44%, H100 PCIe 38% |
| Open picture models: FLUX.2 klein, Qwen-Image-Edit | 63 | 6.0 h | €15.96 | 2.9% | €18.31 | 3 min | two H100 SXM 46%, H100 PCIe 38% |
| Method experiments: terrain, plants, clay, Infinigen | 32 | 14.2 h | €15.74 | 2.9% | €18.05 | 33 min | L4 35%, 32-core processor 28% |
| Sound | 5 | 2.1 h | €1.88 | 0.3% | €2.16 | 5 min | L4 86%, H100 PCIe 10% |
| All | 1,127 | 495.9 h | €547.31 | 100% | €627.74 | | |

<!-- All four tables: python3 tools/costs/costs.py tables paper/evidence/cloud/ledger.jsonl paper/evidence/cloud/ledger-reconciliation.json paper/evidence/cloud/bill-2026-10-10T0136Z.json <out>, saved as paper/evidence/cloud/cost-tables-2026-10.txt (Table G10 excepted). The ledger copy is the ledger's first 1,164 rows, those written by the bill read (costs.py scrub); its October rows started before 2026-10-10T01:36Z are 1,127. The reconciliation file (costs.py reconcile on the same ledger and bill) tags the 55 October rows without a kind by their fields, the exact fields of batch.py's Pixal3D row before score 423c229. Kinds of batch and the R&D rule: tools/costs/costs.py GROUPS, RND_GROUPS, RND_KINDS, RND_WHO; R&D EUR 112.41 and production EUR 434.90 in cost-tables-2026-10.txt. Main card types: the kind's euros by machine type, failed starts that were billed included. The game's engine runs record no machine (machines: []); their types are read from their price as in Table G9 (EUR 22.98 L4, EUR 9.65 POP2-HC-32C-64G). -->

**Table G9.** Rented machines by type, 1 to 10 October 2026, against the price the provider bills an hour. Rentals count the failed starts that were billed. The engine runs' rows name no machine; each is counted under the type whose price gives its cost by the minute (95 under the L4 and 47 under the 32-core 64 GB processor machine).

| Machine | Rentals | Machine time | Cost | Per hour used | Billed an hour | Billed by |
|---|---|---|---|---|---|---|
| L4, 24 GB | 1,080 | 396.3 h | €319.37 | €0.81 | €0.79 | minute |
| H100 PCIe, 80 GB | 148 | 26.0 h | €78.06 | €3.00 | €2.87 | minute |
| 16-core processor, 64 GB | 64 | 20.5 h | €38.44 | €1.87 | €0.59 | started hour |
| 32-core processor, 64 GB | 70 | 21.9 h | €31.79 | €1.45 | €0.85 | started hour |
| two H100 SXM, 80 GB each | 32 | 4.5 h | €31.55 | €7.04 | €6.62 | minute |
| 32-core processor, 128 GB | 38 | 14.8 h | €28.73 | €1.95 | €1.18 | started hour |
| L40S, 48 GB | 45 | 10.3 h | €15.56 | €1.52 | €1.47 | minute |
| P100, 16 GB | 2 | 0.1 h | €2.44 | €17.05 | €1.23 | started hour |
| 16-core processor, 128 GB | 2 | 1.6 h | €1.36 | €0.84 | €0.82 | started hour |
| total | | 495.9 h | €547.31 | | | |

<!-- cost-tables-2026-10.txt, second table: machines[] and billed attempts[] per type (minutes, euros); engine rows typed by costs.engine_type (ceil(minutes) x the bill's price an hour / 60 matches the row's euros: 95 L4-1-24G, 47 POP2-HC-32C-64G). Billed an hour: the bill's euros over its billed quantity per line (paper/evidence/cloud/bill-2026-10-10T0136Z.json), lowest over zones; billed by: tools/props/cloud/backends/scaleway.py price() (cards by the minute, POP2 and RENDER-S by the started hour), and the processor lines' billed quantities equal the ledger's started hours (Table G11). Types: L4-1-24G, H100-1-80G, POP2-16C-64G, POP2-HC-32C-64G, H100-SXM-2-80G, POP2-32C-128G, L40S-1-48G, RENDER-S, POP2-HM-16C-128G. Machine time sums the rows' machine_minutes for the total. -->

The L4 carried 58 percent of the ledger at about its billed price. The processor machines cost 1.6 to 3.2 times their hourly price for each hour they were used, because the provider bills each started hour and their median rental in Blender batches was 12 to 33 minutes. Keeping such a machine for the next batch within the hour already paid, or sending a short batch to a type billed by the minute, would cut this waste. Table G10 gives the cost per unit of work for each kind of batch and card type.

<!-- 58 percent: 319.37 / 547.31. Median rentals: paper/evidence/cloud/capacity-2026-10.txt, "min" column (median minutes a machine was rented) of blender POP2-16C-64G 12.1, POP2-HC-32C-64G 21.1, POP2-32C-128G 32.7. Ratios: 1.87 / 0.59 = 3.2, 1.45 / 0.85 = 1.7, 1.95 / 1.18 = 1.65. -->

**Table G10.** Cost per unit of work by kind of batch and card type, 1 to 10 October 2026, as the capacity report computes it from the same ledger. A unit is one take, render, question, part or picture; seconds a unit is the median, and the cost of a unit is the whole rental of the machines that counted units, setup included, over those units. Rows written before 8 October record no units and are left out of the last three columns.

| Kind | Card | Machines | Failed starts | Units | Seconds a unit | Cost a unit |
|---|---|---|---|---|---|---|
| Pixal3D | L4 | 251 | 32 | 52 | 1,358 | €0.143 |
| Pixal3D | H100 PCIe | 4 | 14 | 19 | 867 | €0.206 |
| Blender | L4 | 220 | 35 | 486 | 116 | €0.159 |
| Blender | 16-core processor | 32 | 0 | 66 | 64 | €0.304 |
| Blender | 32-core processor, 64 GB | 19 | 90 | 34 | 117 | €0.476 |
| Library bake | L4 | 230 | 37 | 208 | 60 | €0.061 |
| Open judge | H100 PCIe | 48 | 89 | 41 | 603 | €0.597 |
| Open judge | L40S | 7 | 64 | 5 | 551 | €0.299 |
| Open judge | two H100 SXM | 19 | 22 | 10 | 416 | €1.357 |
| Parts | L4 | 44 | 113 | 52 | 213 | €0.056 |
| Mesh parts | L4 | 5 | 15 | 7 | 1,059 | €0.291 |
| Mesh parts | H100 PCIe | 4 | 25 | 8 | 1,080 | €0.896 |
| Segments | L4 | 28 | 22 | 63 | 58 | €0.039 |
| Pictures, FLUX.2 klein | L4 | 48 | 2 | 244 | 4 | €0.002 |
| Pictures, Qwen-Image-Edit | H100 PCIe | 7 | 16 | 34 | 85 | €0.093 |
| Characters | L4 | 36 | 3 | 37 | 2,001 | €0.625 |
| Characters | H100 PCIe | 2 | 1 | 1 | 1,285 | €1.768 |
| Rigging (UniRig) | L4 | 2 | 7 | 2 | 68 | €0.033 |

<!-- paper/evidence/cloud/capacity-2026-10.txt: PROPS_HOME=<a folder holding cloud/ledger.jsonl, the evidence copy> python3 tools/props/cloud/capacity.py report --since 2026-10-01, whose table it is (identical to the run of 2026-10-10 01:40Z over the live ledger). capacity.py counts rows without a kind as pixal, as the reconciliation file does. Units per row: models_done, jobs, questions, pictures, takes, makes as each runner records them (unit_seconds, from 2026-10-08 on); euros a unit = euros of the machines with unit_seconds / units, seconds a unit = median. Pixal3D's 52 L4 units come from the rows since 8 October, while its machine count covers all 251. Kinds pictures (FLUX.2-klein-4B) and pictures-20b (Qwen-Image-Edit-2511): tools/props/cloud/pictures.py MODELS. -->

**Table G11.** The provider's bill for October 2026, read on 10 October at 01:36 UTC, against the cloud ledger. The last column prices the ledger's processor machines again by the started hour, as the provider bills them; the engine runs' rows name no machine and are not priced again.

| Bill line | Bill | Ledger | Ledger, processor machines by the started hour |
|---|---|---|---|
| L4, 24 GB | €324.34 | €319.37 | €319.37 |
| H100 PCIe, 80 GB | €73.64 | €78.06 | €78.06 |
| 32-core processor, 128 GB | €50.74 | €28.73 | €50.74 |
| 16-core processor, 64 GB | €41.30 | €38.44 | €41.30 |
| 32-core processor, 64 GB | €34.91 | €31.79 | €32.63 |
| two H100 SXM, 80 GB each | €32.33 | €31.55 | €31.55 |
| L40S, 48 GB | €14.27 | €15.56 | €15.56 |
| P100, 16 GB | €2.45 | €2.44 | €2.45 |
| 16-core processor, 128 GB | €1.65 | €1.36 | €1.65 |
| two small processor machines, no batch | €0.24 | | |
| compute | €575.87 | €547.31 | €573.32 |
| block storage: machines' disks, one kept snapshot | €32.77 | | |
| public IP addresses | €15.09 | | |
| image registry, cluster control plane | €3.50 | | |
| object storage, secrets | €0.51 | | |
| all | €627.74 | €547.31 | |

<!-- Bill: the provider's consumption lines for the month, read 2026-10-10T01:36Z by tools/props/cloud/backends/scaleway.py (the call month_spend() sums), saved without account or project ids as paper/evidence/cloud/bill-2026-10-10T0136Z.json (category, product, sku, unit, billed quantity, euros); not-in-ledger sums: paper/evidence/cloud/ledger-reconciliation.json; per machine type: the last table but one of cost-tables-2026-10.txt (costs.per_product). The processor lines' billed quantities are started hours, and equal the ledger's started hours for POP2-32C-128G (43), POP2-16C-64G (68 in pl-waw-2, 2 in fr-par-2) and POP2-HM-16C-128G (2). The EUR 28.56: 26.01 = 573.32 - 547.31, the repricing (25.16 in rows started before score 423c229, 2026-10-08 11:41Z, and 0.84 in one image build of 2026-10-09); 0.24 = DEV1-M 0.19 + PLAY2-PICO 0.05, with no ledger row; 2.31 = 575.87 - 573.32 - 0.24 (L4 +4.97, H100 PCIe -4.42, two H100 SXM +0.78, 32-core 64 GB +2.28, L40S -1.29). Two small processor machines: DEV1-M and PLAY2-PICO. -->
