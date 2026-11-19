---
title: "SCORE: Synthesising Complete, Owned, Responsive Environments for Simulation"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 19 November 2026"
abstract: |
  Simulation needs worlds that a physics engine can step: separate objects with mass, colliders and joints, a consistent look, and people whose bodies obey the same physics. World generation models now produce convincing pictures, videos and splats of places, yet none of them delivers such a scene, and none hands its creator a file to own and edit. SCORE is an open framework that closes this gap by composing the best current commercial and open-source models around two open foundations, OpenUSD for the scene and MuJoCo for its physics. A creator's concept picture is segmented into objects, the missing objects are generated, every object is finished from one shared library, the assembled scene is checked in simulation, and people are added as musculoskeletal bodies solved by MOTOR. Four places built this way pass every physical check and are written as OpenUSD stages that their creator owns and can edit. Code: https://github.com/Babon-Innovations-b-v/score (MIT).
---

<!--
  Draft conventions (paper/CLAUDE.md). Rewritten from scratch to the owner's outline of 2026-11-18: abstract,
  related work (~300 words), method (<= 400 words, with Figure 1), discussion (<= 400 words, with Figure 3), the walkers' routes in the method with Figure 2 (owner, 2026-11-19),
  references; at most 6 pages. Every number is read from a file, commit or issue comment named in a comment beside
  it; the run records are under paper/score/evidence/place-build/. Scores against the concepts are vision-model
  judgements, never human ratings. MOTOR has its own paper and repository and is cited, not repeated.
-->

```{=latex}
\makeatletter\def\fps@figure{tp}\makeatother\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.1}
```

# Related work

Film met the problem of assembling large scenes from many hands before simulation did. Pixar developed Universal Scene Description for its films and released it as open source in 2016 [@openusd; @pixar2016usd]. A USD stage is composed from layers, so that each department edits its own layer without overwriting the others. In 2023 Pixar, Adobe, Apple, Autodesk and NVIDIA founded the Alliance for OpenUSD to standardise the format [@aousd2023], and its Core Specification 1.0 was ratified in December 2025 [@aousd2025corespec]. The UsdPhysics schema adds rigid bodies, colliders, mass and joints [@usdphysics], and Isaac Lab already trains robots on such stages [@mittal2025isaaclab]. The format can therefore hold a world that is ready for simulation, but every object's physics must still be authored by someone.
<!-- OpenUSD 2012: openusd.org/release/intro.html ("initiated in 2012") [openusd]; open-source release 26 July 2016: openusd.org/dev/press_opensource_release.html [pixar2016usd]; AOUSD founding 2023-08-01 [aousd2023]; Core Spec 1.0 ratified 2025-12-17 [aousd2025corespec]. -->

Physics engines have followed a similar path towards openness. MuJoCo [@todorov2012mujoco], built on generalised coordinates and soft contact, became open source in 2022 [@mujocorepo] and is now a standard tool in robotics and musculoskeletal research [@caggiano2022myosuite]. MuJoCo Warp brings it to the GPU [@mujocowarp; @warp], and Newton, an open engine hosted by the Linux Foundation, uses it as its main solver and reads OpenUSD directly [@newton]. With MyoFullBody, a whole-body model with 416 muscles [@li2026musclemimic], the same engine can carry people as well as objects. What these engines lack is not capability but scenes to run.
<!-- Newton in the Linux Foundation 2025-09-29 (refs.bib note). MyoFullBody 416 muscles: Li et al. 2026 Table 1 and docs/bible.md#architecturelayers ("86 bones and 416 muscles"). -->

World generation models promise such scenes but deliver pictures of them. Genie 3 [@genie3] generates interactive worlds as pixels from a closed model, and Cosmos [@agarwal2025cosmos] predicts video; neither yields geometry that a simulator can load. HunyuanWorld [@hunyuanworld2025; @hyworld2] lifts panoramas into meshes and splats, but with baked colour and without per-object mass or joints. Object generators such as TRELLIS.2 [@xiang2025trellis2] make convincing single assets with no scale and no place in a scene, while procedural systems [@raistrick2023infinigen; @raistrick2024indoors; @yang2024holodeck] keep their scenes explicit but are bound to a fixed grammar or asset set. What is missing is a framework that combines the strongest of them, commercial and open, into one route from a concept to a scene a simulator can step.

# Method

![One place, camp, through SCORE's layers. (a) The creator's locked concept. (b) SAM 3 segments it into 80 instances from its probe nouns. (c) The two objects of camp made by TRELLIS.2, each close-up beside its generated mesh. (d) The assembled place, every surface finished from the place's library palette (strip, 31 tokens). (e) CoACD convex decomposition written with the model (43 hulls for the desk, 48 for the door), with mass, friction and restitution from the material class. (f) A walker's MyoFullBody sim body, solved by MOTOR, in the finished place.](figures/layers.jpg){width=100%}

<!-- Figure 1: (a), (b), (d), (e) from the camp run folders of issue #128 (2026-11-16/17); counts in paper/score/evidence/place-build/camp-figure-2026-11-17.json (sam3_split.instances 80; palette.tokens 31; trellis2_takes_physics hulls 43 and 48). (c) the per-object close-ups (pixal input.png) of camp's two TRELLIS.2 takes (scene.usda score:library model/*_trellis.camp@1: airlock outer door, computer_desk_2) beside their raw meshes. (f) frame at 16.0 s of score-demo-camp.mp4, release demo-2026-11-18 (the final films, assets replaced 2026-11-19). -->

SCORE records every scene as an OpenUSD stage, with its physics in UsdPhysics and each child scene held by reference, so that each of the layers below can be edited without disturbing the others. Before anything is drawn, the creator decides the physics, the setting and the style of the environment: its gravity and ground, where it lies, and a style line with reference pictures. An interview with Gemini 3.1 Pro [@gemini31pro] drafts this environment concept, and the creator locks it.
<!-- docs/bible.md#architecturecomponents (house units), #architecturelayers (UsdPhysics, scene tree), #architecturedesign; score/review/environment_concept.py, setting.py. -->

Each place then passes through the layers shown in Figure 1. Its concept picture is drawn by Nano Banana Pro through the Google Gemini API [@nanobananapro] from the place's contents, view and style, and the creator locks it in turn. SAM 3 [@carion2025sam3] segments the locked picture into an inventory of its objects. A coding agent [@claudecode] lays library pieces over that inventory in Blender [@blender], renders the concept view and corrects the layout until it reads as the concept. Objects that the library does not hold are made by TRELLIS.2 [@xiang2025trellis2] from the concept's own crop of them and fitted in their place.

Generated objects arrive with colours of their own, which would make a scene look assembled from unrelated sources. The library finish therefore moves each generated colour towards the nearest colour of the place's single palette, and replaces any colour that stays far from it with a library surface [@raistrick2026procfunc], so that made and library objects share one look. CoACD [@wei2022coacd] then gives every model convex colliders, with its mass and friction taken from its material.
<!-- tools/props/closeup/pro.py MODEL gemini-3-pro-image; score/review/concept_objects.py PROBES (10), KEEP 40, SAME 0.6; score/stages/place_build/maker/generate.py (TRELLIS.2 take from a close-up, concept crop or picture), maker/fit.py, maker/grade.py GROUPS 6, GRADE 0.6, MISMATCH_DELTA 30 (flagged, repainted with `surface`); maker/sim.py (CoACD hulls, class mass, friction, restitution); maker/setup.sh coacd 1.0.7. -->

The assembled scene is checked before it counts as ready. Twelve kinds of fault are tested, among them objects floating above their support, objects passing through one another and walkways too narrow to use, and in MuJoCo every loose object is released for one second; any object that slides or tips fails the scene.
<!-- score/stages/place_build/ready/__init__.py (12 fault kinds; TOLERANCE 3 cm, WALKWAY 0.9, SETTLE_MOVE 0.05, SETTLE_TURN 8.0; only "unstable" from settle_faults, the rest geometric in resting.py and ready/); ready/settle_mujoco.py SECONDS 1.0, STEP 0.002 (role "prop"; mujoco 3.15.0 in checks-2026-11-17.json). -->

Finally the place is populated. People are routed over the checked floor, animated by Kimodo [@rempe2026kimodo] along those routes as described below, and solved by MOTOR [@motor] as MyoFullBody sim bodies sized to their SOMA bodies [@saito2026soma]. MOTOR recovers the joint motion, computes the ground reaction forces from the contact of the skin with the floor and the joint moments under the place's gravity, and shares those moments over the 416 muscles. A body is accepted when its residual forces and moments stay within the limits of the residual check [@hicks2015verification].
<!-- docs/bible.md#architecturelayers ("131 joints besides the free root: 36 tied, 95 free"; GRF from skin points within 5 mm; static optimisation); score/stages/sim_body/_gates.py RESIDUAL_FORCE 0.02, RESIDUAL_MOMENT 0.01 (Hicks 2015). -->

Each walker is routed over the same floor that the scene check reads. In the manner of Recast [@recast], the scene's solids, shut doors included, are sampled on a 12.5 cm grid into walkable spans with 1.7 m of headroom, joined where the step between them is at most 30 cm and eroded from the walls so that a walkway 0.9 m wide remains; a stair flight is then simply a run of spans one riser apart. Dijkstra's algorithm [@dijkstra1959] finds the shortest route between the walker's spots, which is straightened, rounded at its corners and timed. Because Kimodo makes at most ten seconds of motion per request, the route is cut into walking and climbing pieces, each keyed to the pose that ends the previous one, and a door on the route swings open shortly before the walker reaches it (Figure 2).
<!-- score/stages/place_build/ready/__init__.py walkers_floor, room_for_walkway (WALKWAY 0.9, ERODED 3), doors_standing; tools/usd/reach.py (CELL = BODY_RADIUS / 2 = 0.125, HEAD 1.7, KNEE 0.3, MAX_SLOPE 45; Recast's heightfield of spans); score/stages/walker_route/CLAUDE.md. -->

<!-- ready/__init__.py route (scipy dijkstra over reach.steps_between, edge cost CELL), straightened, in_sight, rounded (ROUND 0.6, TURN_POINTS 7); score/stages/walker_route/__init__.py RATE 30, PACE 1.0, EASE 1.0, STEP_FRAMES 17.25. -->

<!-- walker_route/__init__.py PIECE_FRAMES 210, LEAST_FRAMES 45, OVERLAP 4, TAIL 24, WALKING and STAIRS sentences, on_tread, footed, asked, joined, anchored, grounded (GROUND_EASE 9), posture and slouched (KNEE_STRAIGHT 8.0, SWING_LEAST 0.15, SEED_TRIES 12; "a third of Kimodo's samples walked crouched" in the comment beside them); tools/characters/clips/walker_route.py (Kimodo-SOMA-RP-v1.1, no post-processing on a climb). -->

<!-- ready/__init__.py swing_of (SWING 90.0, ROOM 1.0), opens (score:opens); walker_route/__init__.py door_swings, swung_in (OPEN_AHEAD 1.5, SHUT_AFTER 1.5, SWING_SECONDS 1.0). -->

```{=latex}
\makeatletter\def\fps@figure{!t}\makeatother
```

![The woman's route through the stairwell, drawn in 3D over its stairs, landings and walls. The route is cut into walking and climbing pieces for Kimodo, each joined to the next at a circle, and passes through the given spots (stars). The entrance door is swung open from its shut position (dotted) shortly before she reaches it.](figures/route.jpg){width=100%}

<!-- Figure 2: drawn with matplotlib (3D polygons, this PC's CPU) from the stairwell scene of the release films: its stair flights, floor slabs and far walls cut at the first floor, the entrance door as it stands open and shut (ready walkers_floor doors_standing; entrance_door swung 90 degrees), and the woman's walker_route plan (627 frames; pieces walk 193, up 208, up 181, walk 45 frames; spots) as recorded in paper/score/evidence/place-build/pathfinding-stairwell-2026-11-19.json. -->

<!-- pathfinding-stairwell-2026-11-19.json: walkers (13.451 m, pieces walk 193, up 208, up 181, walk 45 frames; man 19.256 m, walk 210, 209, 210), made (man seeds 2, 302, 102: base seed 2, pieces two and three from later seeds), grounded_lift_m (woman -0.045 to 0.258), measures (skate max 0.0198 and 0.0175, stances 55 and 104, skate over 0; woman route off max 0.1724, standing off ground max 0.1484; within false for both); limits from walker_route/__init__.py SKATE_MOST, ROUTE_MOST, BODY_RADIUS, GROUND_MOST. -->

# Discussion

```{=latex}
\makeatletter\def\fps@figure{!htb}\makeatother\renewcommand{\bottomfraction}{0.7}
```

![(a)–(d) Opening frames of the four released films: camp, campgrounds, street and stairwell. (e)–(g) One walker in the street film, peeled from its player model to its SOMA body to its MyoFullBody sim body solved by MOTOR, with the vertical ground reaction force drawn at the stance foot.](figures/results.jpg){width=100%}

<!-- Figure 3: frames of the release assets of github.com/Babon-Innovations-b-v/score/releases/tag/demo-2026-11-18: the final films, assets replaced 2026-11-19: score-demo-camp.mp4, score-demo-campgrounds.mp4, score-demo-street.mp4 and score-demo-stairwell.mp4 at 0.5 s; score-demo-street.mp4 at 4.0, 9.0 and 14.0 s for (e)-(g). -->

SCORE did not begin with layers. Its first method derived each scene from the concept through model readings, written plans and generated shells. Over the 26 places of a first environment, vision-model reviewers scored the results at a mean of 2.2 out of 10 against their concepts, with wrong shells in 18 places, and eight rounds of fixes did not raise the score. That failure shaped the present design. Current models are strong at single steps, such as segmenting a picture or making one object, and weak at holding a whole scene together; the framework therefore holds the scene itself and calls each model only for the step it does well.
<!-- paper/score/evidence/place-build/old-method-diagnosis-2026-11-16.txt (mean 2.2, 18 and 22 places); issue #128 comments of 2026-11-16 (eight rounds, about 40 commits). -->

With the layered method we built four places: camp, campgrounds, stairwell and street (Figure 3). All four pass the scene check without a fault, on 61 to 1,046 objects each. The building agent's critic scored their concept views between 4 and 7 out of 10, against 1 to 4 for the same places under the old method, although the two sets of judges differ and no human rated either. TRELLIS.2 was judged the better model on five of six camp objects and makes one model in about three minutes on a local 16 GB card.
<!-- Objects and faults: checks-2026-11-17.json (camp 711, stairwell 61) and issue #128 comment "Scene pass 4 (street, campgrounds), 2026-11-17" (github.com/Babon-Innovations-b-v/score/issues/128#issuecomment-6944538261: street 890, campgrounds 1046, 0 faults), the scenes filmed for demo-2026-11-18. round5-and-films-2026-11-17.txt (builder's critic 7/7/4/6; TRELLIS.2 170-220 s; 5 of 6; EUR 0.22; first renders EUR 17); old-method-diagnosis-2026-11-16.txt (reviewing agents: camp 2, campgrounds 4, stairwell 1, street 1); issue #128 comment "Demo done (2026-11-18)" (about EUR 45-50 of the EUR 50 re-film override). -->

The people remain the weakest layer. The walkers keep to their routes, but no sim body yet passes the residual check over a whole clip. In the final stairwell film the woman's sim body no longer sinks into the floor, its deepest foot lying 3.9 cm below the ground against 17 cm in the first film, yet her residual force still peaks at 1,268 N against a limit of 15 N, and only 22% of her frames lie within both residual limits. A revised foot contact in MOTOR reduced the error of each foot's ground reaction force over 13 laboratory trials but raised the residual moment at the pelvis [@motorcontact]. The scenes are not yet photorealistic either: surfaces are clean and pale, kit pieces repeat and signs cannot be read, and the check confirms that objects rest, not that they work.
<!-- walkers-2026-11-17.json (12 of 13 within 6.8 cm; residual peaks and limits); round5-and-films-2026-11-17.txt (17 cm sinking in the first film; look); pathfinding-stairwell-2026-11-19.json final_film_sim_bodies.woman (deepest 0.039 m, largest residual 1268.09 N, limit 14.65 N, frames within residual limits 0.22); issue #128 comment "Demo done (2026-11-18)" ("every walker's residual check fails at its peaks"); score/stages/place_build/ready/settle_mujoco.py GRAVITY 9.81. -->

The next steps follow from these limits: residual limits met over whole clips, articulated joints so that doors and machines can be operated, each place's own gravity in the settle, and an environment rated by people rather than by models. Because each layer is a separate step on an open scene, a better segmenter or generator will replace one step without rebuilding the rest, so the framework improves as the models it composes improve.
<!-- MOTOR contact fix 6d72d73: github.com/Babon-Innovations-b-v/motor/issues/1#issuecomment-6980387981 (13 trials, RMSE down in squats, sit-to-stand, drop jump, walking; pelvis residual moment up 1.5 to 6 N m) [motorcontact]. Disclosure: issue #128; earlier count of co-authored commits in the previous draft (4,211 of 4,238 at e88348ed9). -->

# References {-}

::: {#refs}
:::
