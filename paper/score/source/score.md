---
title: "SCORE: Synthesising Complete, Owned, Responsive Environments for Simulation"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 18 November 2026"
abstract: |
  A single locked concept picture becomes an owned, editable OpenUSD environment that a physics engine can step, populated with people solved down to the muscle. World generation models now render convincing pictures, videos and Gaussian splats of places, yet none delivers separate, editable objects with authored mass, colliders and a consistent finish that have been checked in simulation. SCORE is an open framework that composes current commercial and open-source models around the open OpenUSD standard and the open-source MuJoCo engine. From a creator's concept it segments the picture into objects, generates each missing one, finishes every object from a shared library, checks the assembled scene for physical faults and populates it with people whose MyoFullBody musculoskeletal bodies are solved by MOTOR. Four places built this way pass every check without a fault and are written as stages their creator owns and can hand to a simulator as written; the people remain the open layer, since their sim bodies do not yet meet the residual limits over whole clips. Code: https://github.com/Babon-Innovations-b-v/score (MIT).
---

<!--
  Draft conventions (paper/CLAUDE.md). Rewritten from scratch to the owner's outline of 2026-11-18: abstract,
  related work (~300 words), method (<= 400 words, with Figure 1), discussion (<= 400 words, with Figure 2),
  references; at most 6 pages. Every number is read from a file, commit or issue comment named in a comment beside
  it; the run records are under paper/score/evidence/place-build/. Scores against the concepts are vision-model
  judgements, never human ratings. MOTOR has its own paper and repository and is cited, not repeated.
-->

```{=latex}
\makeatletter\def\fps@figure{tp}\makeatother\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.1}
```

# Related work

OpenUSD began at Pixar in 2012 as the scene description for assembling its films [@openusd] and was released as open source in 2016 [@pixar2016usd]. A USD stage is composed from layers, references and variants, so that each tool edits its own layer. In 2023 Pixar, Adobe, Apple, Autodesk and NVIDIA founded the Alliance for OpenUSD to standardise it [@aousd2023]; its Core Specification 1.0, ratified in December 2025, covers composition and data representation and leaves physics to later domain specifications [@aousd2025corespec]. The UsdPhysics schema already describes rigid bodies, colliders, mass and joints [@usdphysics], and Isaac Lab simulates such stages for robot learning [@mittal2025isaaclab], but every object's mass, collider and joints must still be authored.

<!-- OpenUSD 2012: openusd.org/release/intro.html ("initiated in 2012") [openusd]; open-source release 26 July 2016: openusd.org/dev/press_opensource_release.html [pixar2016usd]; AOUSD founding 2023-08-01 [aousd2023]; Core Spec 1.0 ratified 2025-12-17 [aousd2025corespec]. -->

MuJoCo [@todorov2012mujoco], built on generalised coordinates and soft contact, has been open source since 2022 [@mujocorepo] and is widely used in robotics and musculoskeletal simulation [@caggiano2022myosuite]. MuJoCo Warp ports it to the GPU [@mujocowarp; @warp], and Newton, an open engine under the Linux Foundation since September 2025, runs it as its main solver and reads OpenUSD directly [@newton]. MuscleMimic assembles MyoFullBody, a head-to-toe body with 416 muscles, from MyoSuite's models [@li2026musclemimic]. Each still needs a scene whose physics has been authored.

<!-- Newton in the Linux Foundation 2025-09-29 (refs.bib note). MyoFullBody 416 muscles: Li et al. 2026 Table 1 and docs/bible.md#architecturelayers ("86 bones and 416 muscles"). -->

World generation models do not supply such scenes. Genie 3 generates interactive worlds as pixels from a closed model [@genie3] and Cosmos predicts video [@agarwal2025cosmos]; neither holds exportable geometry or physical state. HunyuanWorld 1.0 lifts panoramas into layered meshes with baked colour and no physical properties [@hunyuanworld2025], and its successor reconstructs splats and meshes with coarse collision but no per-object mass or joints [@hyworld2]. Object generators such as TRELLIS.2 [@xiang2025trellis2] produce single assets with no scale, mass or relation to a scene, and procedural and language-driven systems keep scenes explicit but draw on a fixed grammar or asset set [@raistrick2023infinigen; @raistrick2024indoors; @yang2024holodeck]. What is missing is a framework that composes current commercial and open-source components into one route from a concept to a scene a simulator can step.

# Method

![One place, camp, through SCORE's layers. (a) The creator's locked concept. (b) SAM 3 segments it into 80 instances from its probe nouns. (c) The two objects of camp made by TRELLIS.2, each close-up beside its generated mesh. (d) The assembled place, every surface finished from the place's library palette (strip, 31 tokens). (e) CoACD convex decomposition written with the model (43 hulls for the desk, 48 for the door), with mass, friction and restitution from the material class. (f) A walker's MyoFullBody sim body, solved by MOTOR, in the finished place.](figures/layers.jpg){width=100%}

<!-- Figure 1: (a), (b), (d), (e) from the camp run folders of issue #128 (2026-11-16/17); counts in paper/score/evidence/place-build/camp-figure-2026-11-17.json (sam3_split.instances 80; palette.tokens 31; trellis2_takes_physics hulls 43 and 48). (c) the per-object close-ups (pixal input.png) of camp's two TRELLIS.2 takes (scene.usda score:library model/*_trellis.camp@1: airlock outer door, computer_desk_2) beside their raw meshes. (f) frame at 20.5 s of score-demo-camp.mp4, release demo-2026-11-18. -->

SCORE writes every scene as an OpenUSD stage in metres, its physics in UsdPhysics and its child scenes by reference, so that each layer is edited without disturbing the others. The creator first decides physics, setting and style in an environment concept: its bodies and orbits, each plot's ground and gravity, site coordinates, a style line and reference pictures. A set interview with Gemini 3.1 Pro fills it [@gemini31pro] and the creator locks it; each site's sky is computed from these bodies.

<!-- docs/bible.md#architecturecomponents (house units), #architecturelayers (UsdPhysics, scene tree), #architecturedesign; score/review/environment_concept.py, setting.py. -->

Figure 1 follows one place, camp, through the layers. Nano Banana Pro draws its concept through the Google Gemini API [@nanobananapro] from the place's contents, view and style, for the creator to lock. SAM 3 [@carion2025sam3] segments the locked concept into its inventory from ten generic nouns, keeping up to 40 instances each and merging overlaps above 0.6. A coding agent [@claudecode] lays library entries over it, renders the view in Blender [@blender] and corrects until it reads as the concept. TRELLIS.2 [@xiang2025trellis2] makes objects the library lacks from a close-up or the masked concept crop, fitting each over its placeholder. The library finish moves each of six colour groups 60% of the way to the nearest token of the place's one palette, so that generated and library objects share a look, and flags a group far from every token, which the agent repaints with a library surface [@raistrick2026procfunc]. CoACD [@wei2022coacd] writes convex hulls with each model for downstream simulators.

<!-- tools/props/closeup/pro.py MODEL gemini-3-pro-image; score/review/concept_objects.py PROBES (10), KEEP 40, SAME 0.6; score/stages/place_build/maker/generate.py (TRELLIS.2 take from a close-up, concept crop or picture), maker/fit.py, maker/grade.py GROUPS 6, GRADE 0.6, MISMATCH_DELTA 30 (flagged, repainted with `surface`); maker/sim.py (CoACD hulls, class mass, friction, restitution); maker/setup.sh coacd 1.0.7. -->

The assembled scene is checked for twelve kinds of fault, most of them geometric, among them resting more than 3 cm off a support, interpenetration, tipping and a walkway narrower than 0.9 m. In MuJoCo, every loose object is released for 1 s at a 2 ms step, and one that moves more than 5 cm or turns more than 8° is unstable. Only a fault-free scene is ready.

<!-- score/stages/place_build/ready/__init__.py (12 fault kinds; TOLERANCE 3 cm, WALKWAY 0.9, SETTLE_MOVE 0.05, SETTLE_TURN 8.0; only "unstable" from settle_faults, the rest geometric in resting.py and ready/); ready/settle_mujoco.py SECONDS 1.0, STEP 0.002 (role "prop"; mujoco 3.15.0 in checks-2026-11-17.json). -->

People are routed over the checked floor, animated by Kimodo [@rempe2026kimodo] and solved by MOTOR [@motor] as MyoFullBody sim bodies sized to their SOMA bodies [@saito2026soma]. MOTOR fits the 95 free degrees of freedom of SCORE's variant (131 joints, 36 tied), runs inverse dynamics in Newton under the place's gravity with ground reaction forces from skin contact, and shares the joint moments over 416 muscles by static optimisation. A body passes the residual check when its residual force stays within 2% of body weight and its moment within 1% of weight times centre-of-mass height [@hicks2015verification].

<!-- docs/bible.md#architecturelayers ("131 joints besides the free root: 36 tied, 95 free"; GRF from skin points within 5 mm; static optimisation); score/stages/sim_body/_gates.py RESIDUAL_FORCE 0.02, RESIDUAL_MOMENT 0.01 (Hicks 2015). -->

# Discussion

```{=latex}
\makeatletter\def\fps@figure{!htb}\makeatother\renewcommand{\bottomfraction}{0.7}
```

![(a)–(d) Opening frames of the four released films: camp, campgrounds (cropped), street and stairwell. (e)–(g) One walker in the street film, peeled from its player model to its SOMA body to its MyoFullBody sim body solved by MOTOR, with the vertical ground reaction force drawn at the stance foot.](figures/results.jpg){width=100%}

<!-- Figure 2: frames of the release assets of github.com/Babon-Innovations-b-v/score/releases/tag/demo-2026-11-18: score-demo-camp.mp4 0.5 s; score-demo-campgrounds.mp4 0.5 s, cropped to x 800-1920, y 200-830; score-demo-street.mp4 2.0 s, then 8.5, 11.0 and 13.0 s for (e)-(g); score-demo-stairwell.mp4 0.5 s. -->

SCORE first derived each scene from its concept through model readings, written plans and generated shells. Over all 26 places of a first environment, reviewing vision-model agents scored it a mean of 2.2 out of 10 against the concepts, with wrong shells in 18 places and objects dropped or doubled in 22, and eight rounds of fixes did not improve it. The layered method replaced it for four places: camp, campgrounds, stairwell and street (Figure 2).

<!-- paper/score/evidence/place-build/old-method-diagnosis-2026-11-16.txt (mean 2.2, 18 and 22 places); issue #128 comments of 2026-11-16 (eight rounds, about 40 commits). -->

All four pass the place check without a fault, on 711, 1046, 61 and 890 objects. The builder's own critic scored their concept views 7, 7, 4 and 6 out of 10, the old method's reviewers 2, 4, 1 and 1; with different judges and no human rating, the two sets are not directly comparable. TRELLIS.2 was judged better than the earlier route on five of six camp props and runs in 170 to 220 s per model on a local 16 GB card at no rental cost, against about EUR 0.22 before. First film renders cost about EUR 17 on rented cards, the published re-renders EUR 45 to 50.

<!-- Objects and faults: checks-2026-11-17.json (camp 711, stairwell 61) and issue #128 comment "Scene pass 4 (street, campgrounds), 2026-11-17" (github.com/Babon-Innovations-b-v/score/issues/128#issuecomment-6944538261: street 890, campgrounds 1046, 0 faults), the scenes filmed for demo-2026-11-18. round5-and-films-2026-11-17.txt (builder's critic 7/7/4/6; TRELLIS.2 170-220 s; 5 of 6; EUR 0.22; first renders EUR 17); old-method-diagnosis-2026-11-16.txt (reviewing agents: camp 2, campgrounds 4, stairwell 1, street 1); issue #128 comment "Demo done (2026-11-18)" (about EUR 45-50 of the EUR 50 re-film override). -->

The people are the weakest layer. In the first films of 17 November, twelve of thirteen walkers stayed within 6.8 cm of their routes, but no sim body passed the residual check over a whole clip: the best street walker met the force limit (13.2 N against 15.2 N) but not the moment limit (13.4 N m against 7.4 N m), and the stairwell woman peaked at 1,368 N against 15 N while sinking about 17 cm. The published re-films still fail it at every walker's peaks. The scenes are not photorealistic: surfaces are clean and pale, kits repeat and signs are illegible. The settle runs under Earth's gravity even on Mars, and the check judges rest, not function.

<!-- walkers-2026-11-17.json (12 of 13 within 6.8 cm; residual peaks and limits); round5-and-films-2026-11-17.txt (17 cm sinking; look); issue #128 comment "Demo done (2026-11-18)" ("every walker's residual check fails at its peaks"); score/stages/place_build/ready/settle_mujoco.py GRAVITY 9.81. -->

A revised foot contact in MOTOR lowered per-foot vertical ground reaction force error in all four motions of 13 trials but raised the pelvis residual moment by 1.5 to 6 N m [@motorcontact], so the residual limits remain open work. Articulated UsdPhysics joints would make doors and machines operable, and the settle should take each plot's own gravity. The larger step is a whole environment judged by human raters. Coding agents placed every object through the framework's commands, judged the renders and wrote most of the code; the creator's locks and decisions were his own.

<!-- MOTOR contact fix 6d72d73: github.com/Babon-Innovations-b-v/motor/issues/1#issuecomment-6980387981 (13 trials, RMSE down in squats, sit-to-stand, drop jump, walking; pelvis residual moment up 1.5 to 6 N m) [motorcontact]. Disclosure: issue #128; earlier count of co-authored commits in the previous draft (4,211 of 4,238 at e88348ed9). -->

# References {-}

::: {#refs}
:::
