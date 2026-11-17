---
title: "SCORE: Synthesising Complete, Owned, Responsive Environments for Simulation"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 17 November 2026"
abstract: |
  Games, film, robotics and embodied AI need 3D environments in which every object is a physical body of its own, that remain editable, and that belong to whoever made them. SCORE is an open framework that builds such environments as OpenUSD scenes from a creator's locked concept picture. Its first method derived each scene from that picture through a chain of model readings, plans and generated shells; on 26 places it reached a mean of 2.2 out of 10 against its concepts and no place read as its concept. We replace that chain with kit placement: a coding agent lays pieces from an owned asset library in Blender, renders the concept's own view, compares the render with the concept and corrects, while a physics-readiness check in MuJoCo refuses anything that floats, interpenetrates, tips, blocks a walkway or leaves a door outside its opening. Missing props are made with the open TRELLIS.2 model and graded to one palette per place, real terrain is read from public-domain HiRISE elevation data, and walkers follow routes found on the checked floor, generated as joined Kimodo segments and given a musculoskeletal sim body. On four places the method reaches 4 to 7 out of 10 against the concepts by its own critic, with no physics fault in any place, route error under 7 cm and foot skate under 3 cm for 12 of 13 walkers, although the skate of 7 of them as played exceeds the method's own 2 cm limit; every walker's sim body still fails the residual check at its peaks. Code: https://github.com/Babon-Innovations-b-v/score (MIT).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Main claim: the framework, which synthesises complete, owned, editable environments that are physically
    simulable; building environments is its method, the four places of the 2026-11-16 rethink its evidence
    (issue #128).
  - Every number is read from a file, commit or issue comment named in a comment beside it. The records of this
    rewrite are under paper/score/evidence/place-build/.
  - The scores against the concepts are a vision model's judgement (the building agent's own critic, and the agents
    that reviewed the old method), never a human rating; the paper says so wherever it reports one.
  - The MOTOR solver has its own paper and repository (moved 2026-11-16); it is cited, not repeated.
-->

```{=latex}
\makeatletter\def\fps@figure{tp}\makeatother\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.1}
```

![Each place's locked concept (left) beside the final render of its scene from the concept's own view (right): camp, campgrounds, stairwell and street, top to bottom. Every object in the renders is a library entry laid by the placing agent, and every scene passes the physics-readiness check with no fault.](figures/places.jpg){width=100%}

<!-- Figure 1: concept.png and render.png of each place's final scene (night-<place>-final/scene, 2026-11-17), resized side by side. Checks: paper/score/evidence/place-build/checks-2026-11-17.json. -->

# Introduction

Simulated 3D environments serve games, film, robot learning and embodied AI [@yang2024holodeck]. Across these uses they share a common structure of separate objects with collision geometry and mass, a ground with its gravity, light from identifiable sources, and scenes that can be reopened, modified and simulated again. Authoring such an environment by hand is expensive, and a generative system that takes over this work must leave the result in the hands of its author, since in the Game Developers Conference's 2026 survey 52 percent of game workers considered generative AI to be harming the industry [@gdc2026survey].

World models generate an environment as a sequence of video frames [@bruce2024genie; @genie3] that no physics simulator can step forward in time. 3D environment generators [@wang2025worldgen; @hyworld2] produce geometry, mostly as a single fused asset from which separate objects have to be recovered afterwards [@hu2026worldact; @niu2026worldsculpt]. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] and coding agents that write scenes as executable programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue; @he2026thinking; @wang2026codeasworlds] keep the environment explicit and inspectable, but the models they produce often float above their supports or come apart [@gao2026codebench3d], and such agents assess their own geometry unreliably [@li2026lego]. Open vision foundation models now recover segmentation masks [@carion2025sam3] and 3D shape [@li2026pixal3d; @xiang2024trellis; @trellis2] from single images, and a coding agent can call them as tools, yet none of them provides physical properties, and objects made by different models rarely share one visual style [@wu2026production; @yang2026flowscene].

The components needed for the physics already exist. OpenUSD [@openusd], the scene description that Pixar developed for film production, composes scenes from smaller ones by reference and describes rigid bodies, colliders and mass in the same stage, and MuJoCo [@todorov2012mujoco] is a widely used engine for bodies in contact. What is missing is a route from what a creator intends, typically a single concept picture, to a complete environment in this form that still reads as that picture.

SCORE is a framework for that route. Its environments are complete, since every object, surface and light a scene shows exists wherever the viewer looks; owned, because every model in the framework permits commercial use of its output and every object comes from the creator's own asset library, score_lib; and responsive, because every object carries its collider, mass and material, so a simulator steps the environment as written. This paper reports a change of method. SCORE's first method derived every scene from its concept through a chain of model readings, written plans and generated shells. Measured on 26 places of a first environment, that derivation produced scenes far from their concepts (Section 2). We replaced it with kit placement (Section 3): an agent lays library pieces, renders the concept's own view, compares and corrects, under a physics-readiness check that refuses any scene a simulator could not step. People are then routed through the checked floor and given musculoskeletal sim bodies (Section 4). Section 5 reports four places built this way, with their scores against the concepts, their checks, their walkers and their costs, and Section 6 states what still fails.

<!-- Uses and the main claim: owner, 2026-10-27. The rethink and the four places: issue #128 comments of 2026-11-16 ("Rethink decisions", "House in order"). -->

# Why the per-picture derivation failed

The first method turned each locked concept into a scene in stages, each one a model call or a rule. Gemini 3.1 Pro [@gemini31pro] listed every object of the concept as a row of a scene inventory, and SAM 3 [@carion2025sam3] localised each row with a box. A plan in metres was then written from a drawing of the scene from above, a scene record built shells, stairs and ground from that plan, every inventory row became a model made from a close-up of its crop, and an assembly placed the models by rules on what holds what. Every stage passed measured checks before the next began, and paid stages were bought in phases.

The method was carried to stills of all 26 places of the first environment. Reviewing agents then scored each still against its concept and traced every shortfall to its cause. The mean was 2.2 out of 10, the best place reached 4, and no place read as its concept. The individual models were often fair; what failed was the scaffolding between them. Room outlines, heights and shapes came from the written plan rather than from the concept and were wrong in 18 places, partly because the shell builders could not make several shapes the concepts draw, such as a dome with a rise, a round tube or a sunken pit. Walls, frames, panels and terrain named in the inventory produced no geometry, so most walls were a single flat finish. Fitting a model into its box scaled it by its tightest side, which shrank doors and furniture in 17 places. The reading dropped key objects and doubled others, and each duplicate door cut another opening into a wall. Placement followed generic rules rather than the relations the concept shows, so tunnels were pushed apart from the domes they join and copies were lined up along one wall. Several of these faults cannot be repaired by rules, because a layout read from one isometric picture is ambiguous and a written plan and a concept that disagree need someone to decide which one wins.

<!-- Scores, causes and counts: paper/score/evidence/place-build/old-method-diagnosis-2026-11-16.txt (26 places, mean 2.2/10, best 4; shells 18 places; code rows about 20; fitting 17; reading 22; placement about 24). The old stages: the previous version of this paper, git show 46f2712d:paper/score/source/score.md. -->

Eight rounds of fixes over the following night, about 40 commits, did not change the picture: the creator judged the reworked previews no better and stopped the run. Each fix also re-keyed paid outputs, so that re-buying the 77 paid rows the first rework round touched alone would have cost EUR 85.65. The creator decided to change the method rather than patch its rules, to build fewer places properly, and to remove the per-picture chain (the inventory reading, the plan writing and its fixes, the scene record, the shells and the assembly) once its usable content had been moved into score_lib.

<!-- Rounds and stop: issue #128 comments "Morning status (2026-11-16 08:15 CET)" (8 rounds, about 40 commits) and "Stopped (2026-11-16 ~10:30 CET)". EUR 85.65 for 77 rows: issue #128 wave 1 comment. Decisions: issue #128 comments "Rethink decisions" and "House in order, decisions" (owner, 2026-11-16). -->

# Method: placing a scene from its concept

## The concept and its objects

A place begins, as before, with a concept picture the creator has locked. It is no longer read into rows, counts and a plan. SAM 3, run on a local graphics card, segments the whole picture into objects, each with its pixel box, mask and the word that found it, and an instance that duplicates a surer one under another word is dropped. These objects are the placing agent's list of what the scene must contain; how many there are and where they stand is the agent's to read from the picture, checked against the render.

<!-- score/review/concept_objects.py (docstring); place_build `start --split` (score/stages/place_build/CLAUDE.md). -->

## Kit placement and the concept-view compare loop

The scene is built by a coding agent, Claude Code [@claudecode], through one command-line tool, `place_build`, whose steps lay and adjust a plain OpenUSD stage in metres. Every object it lays is a score_lib entry copied whole into the place: modular kit pieces, models, the dome shells and tunnels, a switchback stair core of real size (0.167 m risers and 0.28 m treads), chamfered building blocks with window openings, lamps and sky domes. A surface step binds a library material over an object or one of its parts, so a model's baked colour never shows where the library has a better finish. Many steps run in one process on one open stage, so a complete relayout takes seconds.

The agent then renders the concept's own view, a camera it sets to match the concept's composition, through Blender's Cycles renderer [@blender], and reads the render beside the concept. A review step renders a contact sheet of the same scene in one call: a plan section 2.4 m above the floor with a metre grid and object names, four corner views, eye-height views from each door, close-ups of each compartment, the concept in a corner and any physics fault boxed in red. From these the agent decides the next correction, such as moving a cluster of props to the side of the room where the concept shows them, changing a dome's height, or swapping a model that reads wrongly. Nothing in the tool judges the scene; it only lays, measures and renders, and the loop ends when the render reads as the concept, with the same room, layout, main objects and mood, while details may differ.

<!-- score/stages/place_build/CLAUDE.md (put, surface, light, stairs with 0.167 m risers and 0.28 m treads, blocks, batch, review, camera); stair_core.py. The bar: issue #128 "Rethink decisions" (owner, 2026-11-16). -->

## One library, one palette a place

Everything a place shows comes from score_lib, and the usable content of the earlier method, the models that had passed their checks, its procedural materials and its code-made kits, was moved there before the old stages were removed. Because scans and models from many sources look inconsistent side by side, each place takes in one scene surface library, a set of procedural material variants written as ProcFunc recipes [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen] in the place's palette tokens, with their wear and dirt. Shells, floors and repainted parts take their finishes from it, so that they share the look of the props.

<!-- One palette a place: score/stages/place_build/CLAUDE.md "One palette a place" (owner, 2026-11-16). About 1,700 models: issue #128 house-in-order inventory (the session's report of the wipe list). Library entries: score_lib commits named in issue #128 comments (2a0144f8, 9d5224ac, 63dbd4ab, 6d0d9980) and the issue's house-in-order decisions. -->

## Props made with TRELLIS.2

A prop that the library lacks, or whose model reads worse than the picture, is made with TRELLIS.2 [@trellis2], an open image-to-3D model released under the MIT licence, from a crop of the concept cut out by its SAM 3 mask or from the close-up of an earlier model. The model is generated on the creator's own 16 GB graphics card, built from source with its dependencies at pinned commits, in 170 to 220 s per prop under load, after about 80 s to load the model. The new mesh is fitted over the model it replaces by quarter turns and one uniform scale, minimising the two-way distance between their point sets. Its own paint is then graded 60 percent of the way toward the nearest palette token, and a colour group that stays far from every token is reported so that the agent can repaint it from the library. Finally the model is made simulation-ready. CoACD [@wei2022coacd] decomposes it into convex hulls for collision, its mass is the hulls' outer surface times the material class's sheet thickness and density, and friction and restitution follow the class. On six camp props the masses lie beside those of the earlier models (a crate of 4.0 against 2.6 kg, a desk of 44 against 42 kg, a chair of 5.1 against 4.7 kg), but steel frames come out heavy, because a hull closes over a frame's gaps. Figure 2 compares the two routes on the same pictures.

![The same six camp pictures (left) made by SCORE's earlier picture-made route (centre three columns) and by TRELLIS.2 (right three columns), each from the front, three-quarter and back. The building agent judged the TRELLIS.2 model the better match on five of the six.](figures/trellis2.jpg){width=88%}

<!-- score/stages/place_build/maker/CLAUDE.md (fit, GRADE, hulls, mass); issue #128 comment "TRELLIS.2 model maker landed" (commits 28dce6914, 55100006a, 5ba41101c; 170 to 220 s a model under load, 8.6 GB of card; masses). Five of six: issue #128 comment "Night run to the demo started". Sizes of the six: paper/score/evidence/place-build/trellis2-sizes-2026-11-17.json. Figure 2: the comparison sheet of 2026-11-16 (trellis2/compare/overview.jpg in the session's scratch), resized. -->

## Real terrain

Outdoor places stand on real ground. A terrain entry is a heightfield read from a public-domain digital terrain model of the HiRISE camera on the Mars Reconnaissance Orbiter [@mcewen2007hirise] (NASA/JPL/University of Arizona), fetched by range requests rather than as a whole file, dense near the place and sparser toward a horizon that bends with the planet. A building's site is levelled to its laid height and eased into the surrounding relief, and loose rocks are set onto the relief at their own footprints.

<!-- score/stages/place_build/relief.py; score/stages/place_build/CLAUDE.md "A real ground". -->

## The physics-readiness check

A scene that reads as its concept may still be one a simulator cannot use, and every round of the compare loop therefore ends with a physics-readiness check. It assigns each object a role from the scene (ground, shell, structure, connector, door, prop, mount, person or far scenery) and reports every fault by object and kind. Each object must rest on a support within 3 cm and stand in balance, and sampled points of its surface must not lie inside another object. A door must lie in an opening, with its outline within 5 cm of the opening's edge, and a connector such as a tunnel must meet the structures it joins within 30 cm with a floor along its length. Every person's feet must touch a floor within 1 cm, and no body may be torn. The walkers' floor is computed as Recast-style walkable spans [@recast] with every solid's footprint removed and eroded to a way at least 0.9 m wide, and it must link every spot a walker is sent to. Ground and fixed pieces more than 20 m beyond anything a walker can reach count as scenery and are left out of every measure. Finally, the props are released as free bodies in MuJoCo 3.15 for one simulated second at Earth gravity, one small model per object with its static neighbours, and any prop that falls, tips or drifts is a fault. Every fault kind has a planted counterpart in the check's test, which must be reported by name. The check never moves anything; the agent corrects and runs it again.

<!-- score/stages/place_build/ready/CLAUDE.md and ready/__init__.py: TOLERANCE 0.03 (tools/usd/resting.py), FIT 0.05, JOIN 0.3, CONTACT 0.01, WALKWAY 0.9 (owner's brief, 2026-11-16), GROUND_REACH 20.0; settle_mujoco.py SECONDS 1.0, STEP 0.002, GRAVITY 9.81; MuJoCo 3.15.0 in every check record (checks-2026-11-17.json). Fault kinds: no support, floating, penetration, tips, unstable, no collision geometry, door not in an opening, door does not fit, connector, walkway, person floating, broken body. Test: test_every_planted_physics_fault_is_told_by_name.py. -->

## A builder tournament

A single agent's layout depends on its early choices, so each place was built by three independent builders that used the same tools, library and check, each trying its own layout. Judging agents compared their concept-view renders with the concept, the best one was kept, and a final builder refined it with the strongest elements of the others. The tournament's per-builder scores were not kept as a record; only the winning scenes and their checks were.

<!-- Issue #128 comment "Night run to the demo started" (2026-11-16 evening: three builders per place competing with judges, then the winner refined). No score record: paper/score/evidence/place-build/round5-and-films-2026-11-17.txt. -->

# People in the place

## Routes and joined motion

Each walker is given spots to pass through and the length of its film. Its route is the shortest way through those spots over the check's own walkers' floor, with doors open as passages and a stair flight as a run of spans one riser apart, its corners kept by line of sight and rounded over 0.6 m, so a route never leaves floor the check has judged. A walker that must fill its film walks on around its spots until it does. The route is then timed at 1.0 m/s on the flat and one tread per step on a flight, eased from standing at the start and back to standing at the end, and cut into pieces of at most 7 s at every start and end of a flight. Each piece is generated by Kimodo [@rempe2026kimodo] in its own canonical frame from the dense path and heading of its stretch, as a flat walk or as a climb with each foot asked onto its tread. Every piece after the first is constrained by full-body keyframes on its first four frames to the pose in which the previous piece stood there, so that position and velocity match across the join. The pieces are joined back in the scene's frame by blending over those shared frames, with the standing foot held on its spot. The travel therefore comes from the clips themselves; a clip is never slid, stretched or looped along a line. Each walker is measured against fixed limits: foot skate per stance of at most 2 cm, the hips within 10 cm of the route, and the body clear of every upright solid between knee and head.

<!-- score/stages/walker_route/__init__.py docstring and constants (PACE 1.0, PIECE_FRAMES 210 at RATE 30, OVERLAP 4, SKATE_MOST 0.02, ROUTE_MOST 0.10); score/stages/place_build/ready ROUND 0.6. Owner, 2026-11-17: "we need like a path finding algorithm, that can splice the path into kimodo makable clips, and fills it then" (score/stages/walker_route/CLAUDE.md). -->

## Sim bodies and the peel

Every walker also receives a sim body, a musculoskeletal twin built on MyoFullBody [@caggiano2022myosuite] that follows its motion on the scene's own ground while MuJoCo supplies the physics. The solver, MOTOR, has its own paper and repository [@motor]. It fits the body to the walker's SOMA body [@saito2026soma] over the whole clip, reduces the residual in the manner of OpenSim's RRA [@delp2007opensim], and records whatever force and moment remain at the pelvis as the residual, which is never applied. The residual check limits that force to 2 percent of the body's weight, after the residual forces AddBiomechanics reports [@werling2023addbiomechanics], and the moment to 1 percent of the weight times the height of the centre of mass. A walker that fails it is reported as failing; it is never stood still or slowed to pass.

Each place's film follows a camera path that holds on the concept's view, glides down clear of every solid of the check and moves through the place's named stops. It ends with the peel, in which the camera closes on one walker and shows in turn its player model, its SOMA body and its sim body with ground reaction force arrows (Figure 3).

![The peel at the end of the camp film: the player model (left), its SOMA body (centre) and its MyoFullBody sim body with its muscles and a ground reaction force arrow under the standing foot (right), walking through the tunnel between the two domes.](figures/peel.jpg){width=100%}

<!-- Sim body: score/stages/sim_body/CLAUDE.md; MOTOR moved to its own repository (paper/CLAUDE.md, 2026-11-16). Limits: score/stages/sim_body/_gates.py RESIDUAL_FORCE 0.02, RESIDUAL_MOMENT 0.01 (owner, 2026-10-28). Keep walkers walking: owner, 2026-11-15 (walkers are the demo's point). Film: score/stages/place_build/film.py and CLAUDE.md "The film"; the peel: commit e88348ed9 (ZOOM_SECONDS, WALKER_HOLDS 4, 4, 8 s). Figure 3: frames at 18, 24 and 27.5 s of the camp film of 2026-11-17. -->

# Results: four places

The creator chose four places from the first environment to rebuild: camp, two glass domes on Mars joined by a tunnel; campgrounds, the open site around them with a lander, a drilling rig and a mast; stairwell, a cut-away switchback stair in a residential block; and street, a rainy night street leading to a launch plaza. They are the three places that carried walkers in the first environment and the outdoor place that had read best under the old method. Figure 1 shows each concept beside its final render, and Table 1 summarises the scenes.

<!-- The four places and why: issue #128 "Rethink decisions" (owner, 2026-11-16). -->

```{=latex}
\begin{table}[tbp]
\centering\small
\caption{The four places. Objects checked and faults are from the final physics-readiness check of each scene, including its MuJoCo settle. Critic scores are the building agent's own judgement of its round-5 renders against the concept, out of 10; the old method's reviewing agents gave the same places 2, 4, 1 and 1. Films are 1920 by 1080 at 24 frames per second.}
\begin{tabular}{@{}lrrrlrr@{}}
\hline
Place & Objects & Faults & Concept view & Other views & Walkers & Film \\
\hline
camp & 711 & 0 & 7/10 & 6/10 insides & 2 & 29 s \\
campgrounds & 369 & 0 & 7/10 & 6/10 eye height & 3 & 34 s \\
stairwell & 61 & 0 & 4/10 & 6/10 insides & 2 & 24.5 s \\
street & 888 & 0 & 6/10 & 6/10 eye, 5/10 wide & 6 & 19 s \\
\hline
\end{tabular}
\end{table}
```

<!-- Objects and faults: paper/score/evidence/place-build/checks-2026-11-17.json. Critic scores: round5-and-films-2026-11-17.txt (round 5). Old scores: old-method-diagnosis-2026-11-16.txt (camp 2, campgrounds 4, stairwell 1, street 1). Walkers: walkers-2026-11-17.json. Films: round5-and-films-2026-11-17.txt and ffprobe of the four films. -->

**Against the concepts.** By the critic's own scores, camp and campgrounds reach 7 out of 10 in the concept's view, street 6 and stairwell 4, against 2, 4, 1 and 1 for the same places under the per-picture method. The scores come from vision models on both sides, the old ones from reviewing agents and the new ones from the building agent's critic, and neither is a human rating; the comparison shows a change of scale rather than a calibrated measure. The renders in Figure 1 support it: the camp's two domes, their tunnel and their furnishing, the campgrounds' layout around the lander, the stairwell's cut-away flights and the street's lanterns, barriers and rain stand where the concepts place them. The critic's remaining notes are concrete. In camp everything is a pale beige and the lockers do not read as suit lockers, in campgrounds the sand ripples are too even and the sky is flat, the stairwell's view shows the building from outside rather than as the concept's cut-away and has no surroundings, and the street has boxy fronts with repeated windows and a garbled cafe sign. The street's missing rain was added afterwards as a code-made library effect, and its blotchy walls were traced to the renderer rather than to the scene, since the review's 16 samples denoised a lamp-lit haze into blotches; reviews of places with haze now render at the films' 64 samples.

<!-- Critic notes: round5-and-films-2026-11-17.txt. Rain (algorithm/rain, rainfall.py) and haze and samples: issue #128 comment "Scene pass 4" (commit 8d642f184, CARD_SAMPLES 64). -->

**Physics.** All four final scenes pass the physics-readiness check with no fault, including the MuJoCo settle of every prop: 711 objects in camp with its scattered rocks, 369 in campgrounds, 61 in the stairwell and 888 in the street. Building the camp also exposed faults in the check and the routing, which were corrected in the code rather than tolerated in the scene. A laptop on a desk with a raised back fell 4.9 m through the desk because the settle had left out what held it, a walker's route through a loop collapsed to zero length when its legs were straightened as one path, and 30 rocks bedded deeper than 10 cm were read as unsupported. One fault was resolved by omission rather than repair: a laptop model whose file leans by about 15 degrees tips in the settle however it is laid, and the camp leaves it out.

<!-- checks-2026-11-17.json. Faults found: issue #128 comment "Night, camp builder 3" (commits fc56ea6c5, 9a396e15f, 591c58dbc; 30 rocks; laptop_1 left out, "Found, not fixed"). -->

**Walkers.** Thirteen walkers were routed and generated in the four places (Table 2, Figure 4). Twelve stay within 6.8 cm of their routes and keep at least 0.48 m from every upright solid. Eleven keep their planted feet within the 2 cm skate limit as Kimodo made them, and one street walker skates 2.9 cm; as played in the scene, foot skate reaches up to 2.9 cm for these twelve, and 7 of them exceed the 2 cm limit. The stairwell woman, who climbs the stair, is the exception on every measure. She strays 18 cm from her route, skates 3.6 cm in Kimodo's output and 4.7 cm as played, and passes within 0.31 m of a solid.

```{=latex}
\begin{table}[tbp]
\centering\small
\caption{Walker measures per place, as ranges over its walkers: foot skate as Kimodo made the clip and as played in the scene, the hips' distance off the route, the least clearance from an upright solid, the peak residual force against its limit (2 percent of the body's weight under the place's gravity, Mars for camp and campgrounds, Earth for the others) and the share of frames within both residual limits.}
\begin{tabular}{@{}lrrrrrrr@{}}
\hline
 & & \multicolumn{2}{c}{Skate (cm)} & Off route & Clearance & Peak residual & Frames \\
Place & Walkers & Kimodo & played & (cm) & (m) & N (limit) & within \\
\hline
camp & 2 & 1.0--1.9 & 2.5--2.9 & 4.0--5.7 & 0.48 & 81--95 (5.7) & 74--87\,\% \\
campgrounds & 3 & 1.5--1.7 & 2.3--2.9 & 4.0--4.7 & 0.76 & 92--263 (5.6--5.7) & 56--82\,\% \\
stairwell, man & 1 & 1.7 & 1.6 & 4.0 & 0.73 & 597 (15.0) & 60\,\% \\
stairwell, woman & 1 & 3.6 & 4.7 & 18.0 & 0.31 & 1368 (15.0) & 39\,\% \\
street & 6 & 1.3--2.9 & 1.3--2.9 & 4.2--6.8 & 0.53 & 13--632 (14.9--15.2) & 79--98\,\% \\
\hline
\end{tabular}
\end{table}
```

<!-- paper/score/evidence/place-build/walkers-2026-11-17.json (every number; ranges computed over each place's walkers). Limits: SKATE_MOST 0.02, ROUTE_MOST 0.10 (score/stages/walker_route/__init__.py). -->

![Walkers from above in camp (left) and the stairwell (right): grey footprints of the solids between knee and head, each walker's route dashed and its hips solid, planted feet as dots, with each walker's foot heights over time beneath. The stairwell woman's route climbs the switchback flights, and her feet follow the rising route ground.](figures/routes.jpg){width=100%}

<!-- Figure 4: wpf-walkers/camp-check.png and stairwell-check.png of 2026-11-17 (the run's own plots), side by side. -->

**The residual check fails.** No walker's sim body passes the residual check over the whole clip. The best, a street walker, holds its force within the limit (13 N against 15.2 N) but not its moment (13.4 against 7.4 N m). In camp the peak residual force is 95 N against a limit of 5.7 N, while 74 to 87 percent of frames lie within both limits and the mean force is 2.4 to 3.2 N, so the failure lies in short peaks rather than throughout. The stairwell is far worse. The woman's peak reaches 1,368 N against a 15 N limit with only 39 percent of frames within, and in her film her sim body sinks about 17 cm. Section 6 discusses what this means.

<!-- walkers-2026-11-17.json (walker_r1 13.21 N, limit 15.19, 13.43 N m, limit 7.4; camp 95.48 N, limit 5.71, frames within 0.736 and 0.872, mean 3.21 and 2.43 N; played skate over 0.02 m: 7 of the 12 walkers other than the woman; woman 1367.53 N, 14.96, 0.385). Sinks 17 cm: round5-and-films-2026-11-17.txt (films). -->

**Films.** Each place's film is rendered at 1920 by 1080 and ends with its peel (Figure 5). The camp film had a final polishing round, in which its walkers walk for the whole film and the peel shows the sim body's muscles and a readable ground reaction force arrow. The other three show open faults. In campgrounds the force arrows are faint, four astronaut figures stand still and one walker starts 4.5 s late, the stairwell's man stops after 7.5 s, and in the street the peel faces the plaza's flat backdrop and most sim bodies have no centre of pressure from which to draw an arrow.

![Frames from the four films: camp (top left), campgrounds (top right), stairwell (bottom left) and street (bottom right), each at about a third of its length.](figures/films.jpg){width=100%}

<!-- round5-and-films-2026-11-17.txt (films). Figure 5: frames at 35 percent of each film (demo/<place>.mp4, 2026-11-17). -->

**Costs.** The four films were rendered on rented cloud graphics cards for about EUR 17, by the run's own record, written while the other three films were being rendered again with the camp film's fixes; those second renders are not counted. No other step of this section rented a machine or bought a model call. The building, the checks, the SAM 3 split, the TRELLIS.2 props, the walkers' Kimodo pieces and their sim bodies all ran on the creator's own computer with one 16 GB card, and the coding agents' own use is not costed here (Section 6). A TRELLIS.2 prop takes 170 to 220 s of that card, against about EUR 0.22 (EUR 0.39 at the high estimate) for a model from the earlier paid picture-made route.

<!-- EUR 17: round5-and-films-2026-11-17.txt and the films page of 2026-11-17 ("about EUR 17", camp polished, "the other three films are still re-rendering"). Free on this PC: score/stages/place_build/CLAUDE.md (render through the card queue; SAM 3 free on this PC's card), maker/CLAUDE.md, walker_route/CLAUDE.md (Kimodo free on this PC's card). EUR 0.22 and 0.39: issue #128 comment "Prices for O1-O3". -->

# Limitations and future work

**The residual.** A residual far above its limit means that the motion, as generated, needs a force that neither the ground nor the body supplies. The clips are kinematically clean, with little skate and close route following, and yet they are not dynamically consistent on their peaks, and on the stair the generated climb does not fit the body that follows it. The residual is recorded and never applied, so the failure is visible rather than hidden, but the walkers cannot yet be offered as physically valid motion. The stairwell woman also fails on route, skate and clearance, which points to the climb pieces and their joins rather than to the solver alone.

**Judgement.** Every score against a concept in this paper comes from a vision model, and a single creator decides what passes. Agents judge their own scenes unreliably [@li2026lego], and the building agent's critic is not independent of the agent that built the scene. A human study of concept fidelity, and independent judges in the tournament with their scores kept as a record, are needed before the scores can carry weight beyond the change of scale shown here.

**Look and scope.** The scenes are not photoreal. Surfaces are clean and often pale, repeated windows and kit pieces show, the stairwell lacks its surroundings and signs are illegible. Four places were built, with walkers on Earth and Mars only. The concepts and the earlier close-ups were drawn by closed models that may change or be withdrawn. The placement itself is an agent's work under the creator's direction, so a place costs agent time rather than money, which this paper has not measured.

**Future work.** Next come the walkers' residuals, through climb pieces that fit the stair, contact in the clip generation and the solver work reported in MOTOR [@motor]; independent judges and a human rating of concept fidelity; the remaining places of the first environment; and the uses that SCORE was built for. A sim body that is true to the individual person, validated against measured forces, would let the same scenes yield layered training data. Each sample would pair a rendered image of a person in a complete scene with the body, its joint moments, its ground reaction forces and muscle forces, and a residual that selects only the dynamically consistent movements [@delp2007opensim; @werling2023addbiomechanics; @huo2026biohuman].

<!-- Person-true body and the data loop: issue #56 (owner, 2026-10-27). -->

**Disclosure.** The creator's locks, picks and decisions are his own, given in conversation with the coding agents. Everything between them was done by coding agents, which placed every object of the four scenes, judged their renders and ran the tournament, and which wrote most of the framework's code under the author's direction: 4,211 of its 4,238 commits list a coding agent as co-author. No scene was edited by hand.

<!-- Commits: git rev-list --count HEAD 4238 and commits carrying "Co-Authored-By: Claude" 4211, at e88348ed9. Decisions in chat: CLAUDE.md "The owner may make every owner-only decision in chat" and issue #128 "cockpit can also go". -->

# Conclusion

SCORE builds environments that a simulator can step and that their creator owns. Deriving a scene from its concept through a chain of readings and written plans failed, scoring 2.2 out of 10 across 26 places, because the scaffolding between good models went wrong in ways that rules could not repair. Placing library pieces under a render-and-compare loop, with a physics-readiness check that refuses anything a simulator could not use, produced four places that read far closer to their concepts, with no physics fault, at a recorded cost of about EUR 17 in rented rendering. Walkers route through these scenes on checked floor with clips joined into one motion, and each carries a musculoskeletal sim body whose residual shows honestly where generated motion is not yet physical. That residual is now the open problem. Once generated movement in complete, simulable scenes passes it, such scenes can supply training data that recorded measurement cannot provide at scale.

# References {-}

::: {#refs}
:::
