---
title: "SCORE: Synthesising Complete, Owned, Responsive Environments for Simulation"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 27 October 2026"
abstract: |
  Games, film, robotics and embodied AI all need 3D environments that can be simulated, in which every object is its own body with collision, mass and joints under the gravity of its ground, editable afterwards and owned by whoever made it. World models give frames no simulator opens, and one-shot 3D generators give one fused scene without separate bodies or clear rights. SCORE is a framework that synthesises such environments. It builds them as studios build scenes in OpenUSD, each scene inside its parent scene and each kind of work on it (layout, surfaces, physics, light, motion, effects, sound and people) in a layer of its own, checked and changed apart from the rest. A creator locks the design from the top down, first an environment concept with its style and physics, then a concept for each scene. Open vision foundation models, procedural tools and coding agents make every layer below, each checked by measured gates before the next is made, and every model allows commercial use of its output, so the creator stays the author. Every step is keyed on its inputs, so an edit reruns only the steps behind it. The result is one OpenUSD environment whose physics a simulator reads as written and Newton steps with MuJoCo's solver. We describe the framework and its method, with a first environment as the evidence, whose four demonstrations remain gaps until its batch has run. Each character also gets a sim body on Newton, driven by its SOMA segment rotations. We close with the route toward bodies true to the person, a data loop in which generated movement, kept only when physically possible, trains models that drive a body's muscles, and layered training sets that pair rendered people with their forces and muscle activity. Code and paper are at https://github.com/Babon-Innovations-b-v/score (MIT licence).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main claim: the framework, which synthesizes complete, owned, editable environments that are
    physically simulable and usable across games, film, robotics and embodied AI; building environments
    is its method, environment 1 its evidence (owner, 2026-10-27).
  - About 4 to 5 pages plus references while gaps are open.
  - Every number is read from a file, commit or issue comment named in a comment beside it.
  - No demo or result from a lost or rejected run: every figure, table and film of environment 1 is a gap
    box until its batch has made it (owner, 2026-10-21). The four demonstrations: owner, 2026-10-27.
  - The walkable reference is one optional step; no result compares it with another model or judges it
    on its own, and its output is credited "Generated using World Labs".
-->

```{=latex}
\makeatletter\def\fps@figure{tp}\makeatother\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.1}
```

::: gap
**Gap: Figure 1, one environment, every layer.** Environment 1 from the top down: its physics (the bodies it stands on and their gravity), a top scene on its site, a parent scene with its child scenes, and one scene opened into its layers side by side (base, settle, physics, light, motion, effects, sound, people). It waits on environment 1's batch.
:::

# Introduction

Simulated 3D environments serve games, film, robot learning and embodied AI [@yang2024holodeck]. They share a structure of separate objects with collision, mass and joints, ground with a gravity, light and sound that come from somewhere, and scenes that can be opened, changed and simulated again. Building one by hand is expensive, and a generator that takes the work over must leave the result in its maker's hands, since in GDC's 2026 survey 52 percent of game workers thought generative AI was hurting the industry [@gdc2026survey].

World models generate an environment as frames [@bruce2024genie; @genie3] that no simulator can step. 3D environment generators [@wang2025worldgen; @hyworld2] produce geometry, mostly as one fused asset from which separate objects are recovered afterwards [@hu2026worldact; @niu2026worldsculpt]. Both work in one shot, so a fault cannot be traced to its step. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] and coding agents that write scenes as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue; @he2026thinking; @wang2026codeasworlds] keep the environment explicit but rebuild a scene that already exists or draw from a fixed library. Their models often float or come apart [@gao2026codebench3d], such agents judge their own geometry unreliably [@li2026lego], and on scenes rebuilt from video the best model scores 0.91 on static scenes but 0.67 on dynamic ones [@shen2026codebench4d]. Open vision foundation models [@oquab2023dinov2] now read shapes [@li2026pixal3d], masks [@carion2025sam3] and depth [@wang2025moge2] from pictures, and a coding agent can connect them as tools, yet none gives one style across objects that different models made [@wu2026production; @yang2026flowscene], and none gives physics.

<!-- 0.91 and 0.67: arXiv 2610.03715 Section 4.2 (strongest model, static versus dynamic families). Citations checked 2026-10-20 against their arXiv pages. -->

The pieces for the physics exist. OpenUSD [@openusd], the scene description Pixar made for its films, keeps each department's work in its own layer file and assembles scenes from smaller ones by reference, and its physics schema states bodies, colliders, mass and joints in the same stage. MuJoCo [@todorov2012mujoco] is a widely used solver for articulated bodies with contact, and Newton [@newton], built on Warp [@warp], runs MuJoCo's solver on the GPU [@mujocowarp] and reads OpenUSD directly. What is missing is a route from what a creator wants to a complete environment in this form.

<!-- OpenUSD: openusd.org "Introduction to USD" (each artist works in their own file, a layer; references assemble assets into scenes), read 2026-10-21. Newton reads the composed stage (add_usd): score/stages/physics/inside/physics_trial.py docstring. MuJoCo Warp maintained by Google DeepMind and NVIDIA as part of the Newton project: github.com/google-deepmind/mujoco_warp README, read 2026-10-27. -->

SCORE is that framework. Its environments are complete, since every object, surface, light and sound a scene shows exists wherever the viewer looks. They are owned, because every model in the framework allows commercial use of its output, so the creator holds the full rights. They are responsive, because every object has its collider, mass and material and what moves has its joints, so a simulator steps the environment as written. They are editable, since each scene is a stack of layers made by keyed steps and a change reruns only what it touches. An environment can be a house on a plot of ground or a system of worlds that move one another.

We contribute the SCORE framework (Section 2), which turns a creator's locked design into one OpenUSD environment that is physically simulable and opens unchanged in a game engine, a robot simulator or a film renderer. Its method (Section 3) builds a scene top down and layer by layer, each stage behind measured gates. The evidence plan (Section 4) comprises four demonstrations on a first environment, left as gaps until its batch has run. Section 5 sets out where the framework goes next, toward simulated people true to the person.

<!-- Uses and the main claim: owner, 2026-10-27 (this rewrite's brief). Scales of an environment: CONTEXT.md "physics" (owner 2026-10-21). -->

# The framework

An environment is one OpenUSD record. Each scene is one stage that sits within its parent scene and holds its child scenes, referenced at the rooms its plan gives them, so opening a top scene opens everything below it. Each scene's layers stack in a fixed order, from a slot for the creator's edit layer on top through people, sound, light, motion, effects, crops, machines, physics, settle, ground and the base laid from the locked plan. Each object, one per real-world object, carries its kind, transform, collider and each part's library surface. The environment's physics is decided in its environment concept (EC) as a plot of ground with a gravity and a sun path, one world, or a system of bodies that move one another, where a real body takes its values from a cited table and an invented one is given by its radius, mass, orbit and spin. The physics layer writes a scene's bodies, mass, joints and the gravity of the body it stands on in OpenUSD's physics schema, so any reader of that schema gets the same scene.

<!-- Layer order: score/stages/assembly/record.py ORDER. Scene tree: score/stages/assembly/scene_tree.py, commit 8f07a249. Physics: CONTEXT.md "physics" (owner 2026-10-21); score/review/setting.py (data/physics/bodies.json, the cited table); score/stages/physics (design.py), tools/usd/physics.py ("written so any UsdPhysics reader gets the same trial": issue #55 comment https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441190720). -->

The creator works in the creator cockpit, one signed-in web page where he locks the design, buys paid work and reviews what the framework reports. An environment is a table of stages read off its designs, and environment 1's has 261 rows. A node is one stage for one scene (`assembly@hangar`) or for the environment, and one runner makes, judges and accepts every node. An approved design then runs without further approval.

<!-- 261 rows: len(score.stages.STAGES) at 68378cc4. The cockpit: CONTEXT.md "creator cockpit"; score/dashboard. Design before the batch: owner 2026-10-20, issue #10 comment 2026-10-20T18:00:28Z. -->

**Keys.** A node is made only when its key has no finish record. The key hashes the stage and scene, its code version, contracts, parameters and seed, the pinned model images, every file it reads and the accepted output of every node it reads. The code version counts only code that can shape the output. Code deciding where and how a job runs changes what a run costs, never what it makes, and is in no key. An edit or a fixed fault moves only its own key and those after it, so only those steps run again. Outputs are kept by content hash and never overwritten.

**Gates and accepts.** Each gate answers pass, fail or unknown, with measures and a reason. Missing evidence is unknown, and unknown blocks like fail. The runner accepts an output by itself when every gate passed and it is no worse than the last accepted one, and later nodes read only accepted outputs. The creator keeps four actions. He may reject an accepted output (every node that read it is then stale), accept a worse one with a reason, waive one gate for one key, and override the runner for one paid run. Agents are kept from these by a store that refuses such records from an agent's process and by a hook.

**Batches.** Paid work is bought as a batch with one estimate. The creator's approval sets the batch's budget across all its tries, and the money guards stop it there. Inside a batch every paid job runs once, and a failed output becomes a batch gap that the completion gate lists. Every paid stage is priced from a unit cost measured on the ledgers. A stage with no measured run has no price, and its estimate is shown apart as a guess.

<!-- Keys: score/graph/__init__.py (own_parts, worked_out_key, node_seed, code, usable), score/graph/_code.py (source_files, FRAMEWORK); commit c3b60928. Gates: score/checks (judge, missing_evidence, overall, blocks, regressions). Accepts and the creator's actions: score/review/__init__.py (accept_automatically, accept, reject, waive), score/store OWNER_AREAS, .claude/hooks/accept_guard.py. Batches: CONTEXT.md "batch", "try" (owner 2026-10-20, 2026-10-26); score/dashboard/checkout/flow.py batch_budget; batch gaps: score/stages/batch_gaps.py, commit 1b61643d. Prices: data/costs/per-unit.json, tools/costs/per_unit.py; guesses kept apart: score/adapters/compute run_price (guess_euros). -->

# Method: building an environment

## From concept to plan

**The environment concept.** The creator first locks the EC, its style and physics together with his reference pictures and the scenes it holds, in a short interview with Gemini 3.1 Pro [@gemini31pro]. An environment plan then places each top scene's site on that ground and works out the sky it sees.

**A concept for each scene, top down.** A concept is then locked for each scene, parents before their child scenes. Each draw is one Nano Banana Pro [@nanobananapro] call, on a concept review page where he marks areas and asks for a new draw. A child scene is drawn only once its parent is locked and planned, on a crop of the parent's concept, so that it fits the parent it stands in.

**Inventory and plan.** Gemini 3.1 Pro lists each object of the locked concept as a scene inventory row, with its kind, count, anchor and size in metres, and SAM 3 [@carion2025sam3] boxes each row. Nothing outside the rows is made or placed. Nano Banana Pro then draws the scene from straight above and Gemini 3.1 Pro writes the plan in metres from that drawing, the concept and the inventory. It gives the outline, walls, openings, levels, stairs, roofs and terrain, each item with its facing, people as the spots they stand on, and the child scenes' rooms. Free checks test that every row is placed as often as it counts, inside the outline and clear of other floor items, that every door and standing spot is reached on foot, and that the child scenes tile their parent. What remains goes back as notes at most twice, and only what is left is a gap. The creator's edits on the plan review page always win and redo what follows.

<!-- CONTEXT.md: environment concept, environment plan, concept review, plan review, scene inventory. Code: score/review/environment_concept.py, environment_plan.py, sky.py, concepts.py, reading.py (gemini-3.1-pro-preview; SAM 3 boxes), plan_drawing.py, plan_writing.py, plan_checks (placed, outside, overlap, reach, tiling), plan_fixes.py (at most two notes rounds, commit dcc9bb14), plans.py (commits 2604f113, d307de88). -->

**Shapes first.** The route is one loop at every scale. A parent scene gets its concept, plan and a rough model, and its plan is split into the shapes of its child scenes. Once those shapes are fixed, every child scene is made in parallel and repeats the loop. The rows `rough-model` and `shell-split` are built and have not run.

<!-- The creator's order: owner, 2026-10-19, issues #10 and #11. Rows: score/stages/rough_model (#15), score/stages/shell_split (#16). No run: paper/evidence/design/design-2026-10-21.txt (rough-model and shell-split records: 0). -->

## Layers from row kinds

A scene's layers are read off its design alone. Each inventory row's kind, found from the reading's noun by one table of rules, says what its objects do (emit, move, lie loose, glow, grow, act or sound). A scene gets an effects, motion, physics, crops or people layer only for rows that do so, and always a light and a sound layer. Each layer is made from its rows by their kind's rule, so a new environment needs no hand-written list. The scene record holds what no made piece covers (shells, stairs, ground and water, backdrop, lamps and neighbours), gated on the shell lying within 5 cm of the plan and every doorway opening onto a floor.

<!-- Row kinds: score/stages/row_kinds.py, data/checks/row-kinds.json, score/stages/design_layers.py, commits be088c14, 99d19861, d8012846. Scene record: score/stages/scene_record (gates.py: game-free, plan-matched, openings, TOLERANCE = 0.05). -->

**Models.** Objects take the prop route first. Nano Banana Pro draws its close-up from its crop of the concept and redraws it at most three times when the shape check rejects it. Pixal3D [@li2026pixal3d] builds the model, and a likeness gate compares its outline from eight sides with the close-up. Only an object whose checks fail is built by a code builder a coding agent writes, and a thin straight thing (a pipe, post or beam) whose every close-up failed is swept along its length in code.

<!-- Prop route first: score/stages/props/CLAUDE.md (owner 2026-10-12). Retries: tools/props/closeup/stage.py PRO_TAKES (owner 2026-10-24). Likeness: likeness.py (eight outlines). Thin straight things: commit 546a2ba3 (owner 2026-10-25). -->

**Surfaces.** Everything a scene shows comes from the creator's library, score_lib, or is a written exception. A model gives shape only, and each part takes one surface from a library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen] and coloured from the scene's palette. The finish route labels each face from free renders of the model, matches each finish to a library surface, bakes it and checks the bake against the close-up, with each finish within ΔE 32 of its colour there. A free library check traces every material, model, light, sound and character of an accepted assembly to the library or an exception.

<!-- The library rule: owner 2026-10-18, commit 4c8d3b4d; data/checks/library-exceptions.json; score/stages/complete/library. Finish route: score/stages/surfaces/CLAUDE.md (owner 2026-10-20, #18), finish_parts.COLOUR_DELTA_E 32, commit 5c1e82b6; bake_check.py CLOSE_UP_DELTA_E 32.0. -->

**Settle and physics.** Loose objects are dropped onto the made ground, and one that would turn more than 15 degrees or drift more than 30 cm is a resting fault and keeps its laid pose. The settle writes where each object rests as a layer. The physics trial then steps the composed scene on Newton, with MuJoCo's solver on Newton's contacts under the gravity of the body the scene stands on, and judges it by the gates `reacted`, `at rest`, `energy` (no rise in undriven energy) and `hinge` (a hinged leaf swings to its limit). The trial moved from Blender's Bullet [@bullet] to Newton on 27 October 2026. On a toy scene at Moon gravity (two crate drops, a driven door with a wheel fixed to it, a pushed stool), both engines gave the same answers on every gate, and Newton landed the crates on their targets where Bullet left its contact margins of 8 mm. Newton's deterministic mode, bitwise equal over six runs on that toy, cannot hold scenes with many loose bodies (its buffers pass the 32-bit limit), so the trial and the settle run without it. Two runs of a 25-body toy then agree within 5e-7 m on every body but one that falls off the floor's edge. <!-- deterministic six runs: https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441728558; 25-body toy without it: https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6446507856 --> The settle moves to Newton the same way, so one engine steps what comes to rest and what is tried, and one effect is stepped on Newton as a first case for the effects layer.

<!-- Settle and one effect on Newton, part of the framework before shipping: owner, 2026-10-27 (this rewrite's brief); settle today on Bullet: tools/usd/settle.py. tools/usd/settle.py TURN_MOST 15, DRIFT_MOST 0.3; score/stages/settling. Physics trial on Newton: commit c76fc1e4; score/stages/physics/inside/physics_trial.py. Decision to replace Bullet outright: https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6440766961 (owner, 2026-10-27). Bullet baseline (Moon gravity 1.62 m/s^2, +0.008 m over table and floor): https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6440856171. Newton on the same toy (+0.000 m, same gate answers: reacted, hinge, energy pass, at rest fail for the pushed stool in both): https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441190720. Six runs bitwise equal with Newton 1.7.0 deterministic (not pinned yet, two-week rule): https://github.com/Babon-Innovations-b-v/score/issues/55#issuecomment-6441728558. -->

**Light, motion, effects and sound.** The sky is worked out from the EC's physics, never drawn, with each body at its true direction, size and phase as seen from the scene's site. The lamps are the inventory's glowing rows. One render per scene gives each lamp its own light group, and a free sweep mixes their strengths to bring the scene within 1.5 times its concept's brightness. Every object of a moving row moves by its kind's rule at a speed cited from real machines, gated on nothing coming within 3 cm of another thing. Emitters are measured against real footage. Each sound source gets a library file or one MOSS-SoundEffect [@moss2026] take, gated on a CLAP [@wu2022clap] score of at least 0.30.

<!-- Sky: score/review/overhead.py, score/stages/light/sky.py. Light: score/stages/light/mix.py (BRIGHT_WITHIN 1.5). Motion: score/stages/motion, data/checks/motion.json, REACH_MOST 0.03. Effects: score/stages/effects, data/checks/effects.json. Sound: score/stages/sound/gates.py CLAP_FLOOR 0.30. -->

**People.** People are models like any other, each made from a close-up per person row, built by Pixal3D and painted by the finish route. SOMA's body [@saito2026soma], read from the close-up by SAM 3D Body [@yang2026sam3dbody], is fitted under it as its rig and moved by Kimodo's clips [@rempe2026kimodo]. A shell gate passes a look when 99 percent of its soft points lie within 5 cm of the body. Each person stands on a person spot of its scene's plan.

**Sim bodies.** Each character also gets a sim body, its physical twin on Newton, so people in an environment are simulated as well as animated. The minimal body is built straight from SOMA's 23 segments with a ball joint at each SOMA joint frame. It is driven by the character's SOMA segment rotations without scaling or per-person setup, its mass spread by its segment volumes, and stands on a SCORE floor so its ground forces come from contact. Muscles enter as a minimal first step. Built this way, the body follows SOMA's rotations to within 6.9e-9 m, and on Newton it matches plain MuJoCo to 3.4e-8 after 200 steps.

<!-- score/stages/people/CLAUDE.md; score/stages/people_bodies/bodies.py (SHELL_SHARE 0.99, OFFSET_MOST 0.05); score/stages/cast. Sim body: CONTEXT.md "sim body"; issue #56 (Destination); minimal first, part of the framework: owner, 2026-10-27 (this rewrite's brief). 23 segments, 6.9e-9 m, 3.4e-8 after 200 steps (Newton 1.6.1 against plain MuJoCo): https://github.com/Babon-Innovations-b-v/score/issues/58#issuecomment-6441806660. -->

::: gap
**Gap: Newton for the settle, one effect and the sim body.** The settle and the physics trial on one engine, with the resting and physics gates per scene against the Bullet settle; the one effect stepped on Newton; and a sim body walking on a SCORE floor, its joint angles and ground forces against OpenCap's LabValidation motion capture and force plates [@uhlrich2023opencap]. It waits on these three stages being built and run on a cloud card.
:::

**Completion.** A scene is complete when its gate passes on its final assembly, with every row made or dropped with a reason, nothing unmade, no resting fault, and every layer and shown scene present. A fault the creator ships with is an accepted gap, written with who decided, when and why. The gate lists every gap by name and is never loosened. A hook stops an agent claiming a scene is done while its gate fails, as agents judging their own scenes agree with a measured geometry score only 45.8 percent of the time [@li2026lego]. A complete scene's films are made from scripts the creator locked.

<!-- score/stages/gaps.py; tools/usd/complete.py CHECKS; .claude/hooks/completion_guard.py. LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. Films: score/stages/demo_film, commits 8c89174a, fe4c675d. -->

# Evidence: environment 1

Environment 1 is the evidence. The creator did not accept its first run and its store was lost on 19 October 2026, so this draft shows none of its outputs, and each demonstration below is made on its new batch. Figure 1 is the first.

<!-- The creator's review: issue #10 body. The loss: docs/bible.md architecture/failure ("Losing $PROPS_HOME", 2026-10-19, #13). Demonstrations: owner, 2026-10-27. -->

::: gap
**Gap: Demonstration 2, physics that holds.** Environment 1's scenes stepped on Newton under their own body's gravity: loose objects come to rest, doors swing on their hinges, with the physics trial's gates per scene and Bullet run on the same scenes as the baseline. It waits on environment 1's batch and on Newton taking over the settle.
:::

::: gap
**Gap: Demonstration 3, one environment, many uses.** The same OpenUSD environment opened unchanged in a game engine, in a robot simulator and in a film render, with what each reads of its layers and what it drops. It waits on environment 1's batch and on the engine adapter.
:::

::: gap
**Gap: Demonstration 4, an edit that stays cheap.** The creator changes one thing in a locked scene, and only the nodes whose keys it moves run again; the nodes rerun, time and euros against a full rebuild. It waits on environment 1's batch and on the edit layer being carried from one assembly to the next.
:::

::: gap
**Gap: Table 1.** Per scene of environment 1: inventory rows, models generated and code-built, layers, gaps before and after the batch, time, euros and the creator's verdict. It waits on environment 1's batch and the creator's review.
:::

**Disclosure.** The creator's locks, picks, accepts and waivers are his own clicks, and everything between them is automatic. Coding agents wrote most of the framework's code under the author's direction, and 2,413 of its 2,436 commits carry a coding agent as co-author. Hand fixes to a scene are recorded as the creator's edits.

<!-- Commits: git log at 2f6c81ef (rev-list --count HEAD 2436; messages with "Co-Authored-By: Claude" 2413). The creator's actions: score/review/__init__.py; his edits recorded with his words: CLAUDE.md "Design edits the owner asks for". -->

# Future work: people true to the person

The minimal sim body is a start, and what follows are goals rather than results.

The sim body is to become fully musculoskeletal and true to the person, older people and a curved spine included, instead of a resized template. Joint centres are to come from bone landmarks on its SOMA mesh, then mass, muscles, joint ranges, spine and bone shape, each input SOMA lacks marked as assumed with a range. A full musculoskeletal body with 416 muscles already runs on Newton but still drifts 1.5 cm from plain MuJoCo after 300 steps, so Newton is to be validated for bodies first. Its joint angles, then its joint moments and ground forces, are to be held to OpenCap's LabValidation data.

<!-- Person-true body: issue #56 decisions (owner, 2026-10-27), issue #64 (build order; inputs SOMA lacks marked assumed). 416 muscles and 1.5 cm after 300 steps (MyoFullBody on Newton 1.6.1 SolverMuJoCo after six import fixes): https://github.com/Babon-Innovations-b-v/score/issues/63#issuecomment-6441625310. Newton validated for bodies first: issue #56 decisions. LabValidation licence (Apache-2.0, fetched on demand, never committed): https://github.com/Babon-Innovations-b-v/score/issues/57#issuecomment-6441121325. -->

Motion is to come from the SOMA ecosystem, with GEM-X [@gemx] reading it from video, Kimodo [@rempe2026kimodo] making it from sentences without limit, and sequences joined from datasets of both. The terrain a motion implies becomes a SCORE scene, so the scene keeps the motion without video or anything identifying a person. A sim body follows each movement exactly on its scene's ground, and physics computes the ground contact, the joint torques and the forces of the 416 muscles the movement needs. What neither the ground nor the muscles can supply is the residual, recorded for every frame and never applied, so it measures how physically possible the movement is, and only movement with a small residual is kept. Biomechanics already reduces and reports this residual as a measure of the quality of recorded motion [@delp2007opensim; @werling2023addbiomechanics], and PhysibleMDM [@stolzle2026physiblemdm] lowers an inverse-dynamics residual to make generated motion feasible for a torque-driven robot. We apply the same check to generated motion played through a muscle-driven body.

A brain is a trained model that drives a sim body's muscles so it moves on its own. Trained on the kept movements together with the muscle forces that produce them, it is placed in SCORE's synthesised worlds under their own gravity and ground, where it is to adapt to structures no recording holds, and every run it drives makes data for the next brain. Muscle-driven controllers such as KINESIS [@simos2025kinesis] and MuscleMimic [@li2026musclemimic] learn from motion capture, as torque-driven ones such as PHC [@luo2023phc] do. To our knowledge, no muscle-driven controller has yet been trained on generated motion filtered by its residual, and the claim holds only once such a brain is compared with one trained on motion capture and with one trained on the same generated motion unfiltered.

The same runs can yield layered training sets. Each sample is a rendered picture of a clothed person in a full scene, paired with exact values for every layer beneath it, from the SOMA body and joint angles, the ground force under each foot from simulated contact and the muscle activations and forces to the residual, depth, segmentation and the scene's layout. Such sets are meant for models that go from video to forces or muscle activity. BioHuman10M [@huo2026biohuman] already pairs video, rendered clips among it, with the activations of a 112-muscle body and with ground forces estimated by a learned model from recorded motion. Our sets would differ in scenes made for the purpose in any light, ground and clothing, in forces from contact with each scene's own ground, in a 416-muscle body and in a residual for every sample, and their worth rests on a model trained on them carrying over to real force-plate and muscle recordings.

Specialised brains, for example for clinical groups, would be trained outside SCORE on data that never enters it. The value of the loop grows with the compute put behind it, since every scene, movement and run adds data, which is why SCORE is open, so that others can put their own compute behind the same framework and share the sets they make back.

<!-- Motion sources and the data loop: issue #56 decisions and "Vision (owner, 2026-10-27)". Residual recorded, never applied, and the route to the brain (endless Kimodo movements, hence "without limit", kept by low residual, trained with their muscle forces): issue #56 decisions (owner, 2026-10-27); CONTEXT.md "residual", "brain". Layered training sets: issue #56 "Not yet sharp" (owner, 2026-10-27). Prior work and claim strength: novelty check, https://github.com/Babon-Innovations-b-v/score/issues/56#issuecomment-6451238771 ("to our knowledge first" needs the comparison; BioHuman10M close, no first claimed). PhysibleMDM: inverse-dynamics residual, custom bipedal robot (arXiv:2610.30500 abstract). KINESIS: 1.8 h of locomotion data (arXiv:2503.14637 abstract); MuscleMimic: SMPL-format motion capture onto a 416-muscle body (arXiv:2603.25544 abstract). BioHuman10M: ULBS-112 with 112 muscles, GRFs estimated with GaitDynamics, BEDLAM rendered clips (arXiv:2605.14772, sections 3 and 4). Open: MIT licence (LICENSE); clinical models outside SCORE: issue #56 "Vision". -->

# Limitations and conclusion

One creator judges, and he has not yet accepted a run. Closed models (Nano Banana Pro, Gemini 3.1 Pro) draw the concepts and close-ups and read and plan every scene, and may change or be withdrawn. The design step, the layers from row kinds, the finish route, the shapes-first loop and the scene tree have not yet carried a scene through a batch. The edit layer is a slot. The settle, the effects and the sim body are not yet on Newton, and no game engine or robot simulator has yet opened the result. Next come environment 1's batch with its four demonstrations, an engine adapter, the edit layer carried across assemblies, more environments, open models replacing the closed ones, and the data loop, in which residual-filtered generated movement trains brains whose worth a comparison with motion capture has yet to show. SCORE synthesises an environment as studios build one, scene by scene and layer by layer, in a form a simulator steps as written, and an accepted environment will show whether it holds.

<!-- Engine: score/adapters/engines ("no game engine yet"). Closed models: score/review/concepts.py, reading.py, plan_writing.py, score/stages/props. Edit layer slot: tools/usd/export.py, tools/usd/test_a_creators_edit_survives_a_regenerated_base.py. -->

# References {-}

::: {#refs}
:::
