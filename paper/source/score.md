---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 15 October 2026"
abstract: |
  Games, films and robot training need 3D worlds that are complete, editable and owned by their makers; world models and one-shot generators give frames no engine opens, or one fused scene without separate objects or clear rights. Studios build worlds in stages, from concept art to review. SCORE keeps these stages and automates them with open vision foundation models, procedural tools and coding agents, while the creator chooses and reviews. Every stage is a node of one runner: its output is keyed on its inputs and code, judged by gates that answer pass, fail or unknown, and accepted only when nothing got worse, so a fault is fixed in its own stage and only what follows it runs again; paid steps are cleared against a budget read from the provider's bill. Every model allows commercial use of its output, so the creator stays the author. We describe the framework as built for its first world, the game world of 2099 with 18 places, and the measured gates of its surfaces, resting, light, motion, effects, sound and people. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT license).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; what is not made is on the named-gaps
    list, with what it waits on.
  - Main text: the three contributions only (the staged framework, its stages and gates, the evidence),
    about 4 to 5 pages plus references while gaps are open. The appendix holds only the evidence
    behind a claim the main text makes.
  - Every number is read from a file named in a comment beside it.
  - Only demos that were made are shown or described; an unmade one is on the named-gaps list (Table 3),
    never a plan in the text.
  - The world step is one optional step; no result compares it with another model or judges it
    on its own, and its output is credited "Generated using World Labs".
-->

```{=latex}
\makeatletter\def\fps@figure{t}\makeatother
```

# Introduction

Interactive 3D worlds are the raw material of games, film and embodied AI [@yang2024holodeck], and building one is expensive: every object is modelled, surfaced, placed, given collision, lit and given sound in one style, and the world stays editable. Generative models promise to take over much of this, but in GDC's 2026 survey 52 percent of game workers thought generative AI was hurting the industry [@gdc2026survey]; a tool for building worlds has to leave the result in the creator's hands.

World models generate a world as frames [@bruce2024genie; @genie3] that no engine can open. 3D world generators [@wang2025worldgen; @hyworld2] produce geometry, but mostly as one fused asset, from which separate objects are recovered after the fact [@hu2026worldact; @niu2026worldsculpt]. Both work in one shot, so a creator cannot find or change the step behind a fault. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] and coding agents that write scenes as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue] keep the world explicit, but rebuild a scene that already exists or draw their objects from a fixed library, and such agents judge their own geometry unreliably [@li2026lego]. Open vision foundation models [@oquab2023dinov2] now read shapes [@li2026pixal3d], masks [@carion2025sam3], depth [@wang2025moge2] and parts [@lin2025partcrafter] out of pictures, and a coding agent can connect them as tools; none of them provides one style across objects that different models made, which the field names as an open problem [@wu2026production; @yang2026flowscene].

Studios build worlds in stages, each with an output a person can check; SCORE keeps these stages and automates them. Its worlds are **complete**: every object, surface, light and sound exists wherever the player looks. They are **owned**: every model in the framework allows commercial use of its output, so the creator stays the author, holding the full commercial rights. They are **responsive**: every object has real collision, mass and material. And they can be any kind of **environment**. To our knowledge, no other openly available world generation work joins vision foundation models into engine-ready scenes that are built from reference pictures, steered by a person's choices at each step, and made only with models that allow commercial use of their output.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Hand-off pattern: material/11-vision-foundation-models.md. -->

We contribute **the SCORE framework**, stages as nodes of one runner that keys, judges and accepts every output over one canonical scene (Section 2); **measured gates** for every layer of a place and a completion gate over them (Section 3); and **evidence from a first world**, with its spend per stage (Section 4).

# The framework

A world is a table of stages; world 1's has 95 rows. A **node** is one stage for one place (`assembly@hangar`) or for the world, and one runner makes, judges and accepts every node. The creator's picks (concepts, style, references) are the inputs; from there everything runs without a typed yes, and the creator reviews.

<!-- 95 rows: len(score.stages.STAGES) at 4c5365e. Picks as inputs, no typed yes: the owner's answers of 2026-10-11 on issue #6 (design approved, decisions 1 to 3). -->

## Keys, gates and accepts

**Keys.** A node is made only when its key has no finish record. The key hashes the stage and place, a code version, the contracts of its output and inputs, its parameters, a seed derived from the world's, the pinned model images, every world file it reads and the accepted output of every node it reads. The code version hashes every source file the stage imports, leaving out the runner and the renting code, which change what a run costs, not what it makes. A fault fixed in one stage moves only its key and those after it. Outputs are kept by content hash, never overwritten.

**Gates and accepts.** Each gate answers pass, fail or unknown, with measures and a reason; missing evidence is unknown, and unknown blocks like fail. The runner accepts an output by itself when every gate passed and it is no worse than the one accepted before: no answer dropped, no measure moved the wrong way by a step a viewer could see, no gate missing. Later nodes read only accepted outputs. The creator keeps four commands, from his own terminal: reject an accepted output (it moves back to the one before, and every node that read it is stale), accept a worse one with his reason, waive one gate for one key, and override the runner for one paid run. When he accepts a worse output, his accept records what he allowed, and a later output no worse than the one he took is accepted with his accept named. None is needed for a run; a barrier keeps agents from them (a terminal, a store that refuses the creator's records from an agent's process, and a hook).

**Spending and review.** A paid node is cleared only when every gate on its inputs passed and the month's ceiling has room for its estimate (Section 3.7); everything that rents a machine or calls a paid model refuses without that ticket, and buying again more than EUR 5 of accepted outputs needs a written reason. Each node's review page is built from the store alone, and the creator reviews a place in a USD viewer on the store's copy of its accepted assembly; nothing is rendered for review.

**The creator steers: the ship.** Figure 1 shows the creator's control on one piece of world 1, the ship. His picks were found pictures of a shuttle, a one-deck cutaway, a cockpit and crew quarters; we do not show them. From them an agent planned the bridge alone (v1, a 4.6 by 4.6 m room of 27 pieces). He corrected the plan in words: a smaller cockpit, rooms the game needs, a long flat wedge rather than a rocket, a nose less pointed, and an outline measured from drawings rather than shaped from words. Each correction made a new plan, and he accepted the seventh. Every plan is ours and cost nothing; the two drawings the outline was traced from cost EUR 0.28 and are not shown. The ship's shape follows found artwork the creator chose to use: shuttle concept by PAUL (zana), found online.

![The creator steers the ship's plan, in twelve steps: his picks, described in words (found pictures, not shown); plan v1 of the bridge alone; his corrections; v2 of the whole ship; his correction of the outline; v3 to v6; his two corrections of the nose; v7, which he accepted. All plans are ours. Shuttle concept by PAUL (zana), found online.](figures/fig-k7.jpg){width=88%}

<!-- Figure 1: demo K7, paper/evidence/demos/K7.txt (steps, v1 4.6 x 4.6 m and 27 pieces, drawings EUR 0.28, plans EUR 0, his ok to v7); the locked plan v7 as world data: commit 5ea06fe7. Found pictures and every drawing made from them are kept out of the repository (overseer's decision, 2026-10-14). -->

<!-- Keys: score/graph/__init__.py (own_parts, worked_out_key, node_seed, code, usable), score/graph/_code.py (source_files, FRAMEWORK). Contracts and store: score/contracts, score/store. Gates: score/checks (judge, missing_evidence, overall, blocks, regressions). Accepts and the creator's commands: score/review/__init__.py (accept_automatically, accept, reject, waive), score/review/__main__.py (terminal check), score/store OWNER_AREAS, .claude/hooks/accept_guard.py. Clearance: score/adapters/compute/__init__.py (clearance, month_refusal, require_cleared). Re-buys: score/graph/rebuy.py LIMIT = 5.0. Review in the viewer, no renders: commits f63212c, 4c5365e. -->

## From concept to scene

**Inventory, plan and record.** A coding agent lists every visible element of the concept as an inventory row (kind, anchor, size, count) or drops it with a written reason; nothing is made or placed that is not a row. It draws a dimensioned plan, gated on `mapped` (every element a row, a door or a written drop; every door says where it leads). The scene record is written from the plan, inventory, made ground and sky, gated on `game-free` (nothing copied from the game the world came from), `plan-matched` (the shell within 5 cm of the plan), `openings` (every doorway onto a floor, no view into nothing) and `seed-matched` (every old entry matched or dropped with a reason).

**The canonical scene.** Every place is one OpenUSD stage [@openusd]; each object, one per real-world object, carries its kind, transform, collision and each part's library surface. Its layers lie in a fixed order, the creator's edit layer on top, then people, sound, light, motion, effects, crops, machines, settle, ground and the generated base, so an edit survives a regenerated base. Each place is assembled once, from every layer's accepted output; its `layers` gate answers unknown while a needed layer has none, and an old output never stands in.

<!-- Inventory rule: the owner's rule of 2026-10-08; issue #130, 2026-10-07T23:04. Plan and record: score/stages/scene_record (plan.py, gates.py: TOLERANCE = 0.05). Layer order: score/stages/assembly/__init__.py ORDER; layers gate: judge_layers; needs per place: data/checks/contents.json. -->

**Models, generation first.** Every object goes the prop route first: Nano Banana Pro [@nanobananapro] draws its close-up from its crop of the concept, Pixal3D [@li2026pixal3d] builds it, the surface stage paints it, and a likeness gate compares its outline from eight sides with its close-up. Only an object whose checks fail is built by a code builder a coding agent writes, reversing the earlier parts check (the creator's choice, 12 October 2026). On 13 of the hub's objects both orders end the same (Table 1, Figure 2), but generation first draws a close-up of every object. Every close-up of eight thin and flat objects failed the shape check, so code builds carry them. The hatch wheel shows the gain: its code build's outline overlap was 0.45, a fail, and its generated model's 0.60. Most of world 1's models predate the change and enter as unverified seeds.

**Table 1.** How 13 hub objects, chosen to cover the kinds, end in each order. Close-ups cost EUR 8.12 and the sample's prop route EUR 13.80, about EUR 2.20 an object; no take was baked (the run stopped at the keyboard's paint gate).

| Order | Prop route | Code build | Needs a new builder |
|---|---|---|---|
| Generation first | 4 | 7 | 2 |
| Code first | 4 | 7 | 2 |

<!-- paper/evidence/compare-hub/table.json (counts, euros, unit costs, rows: hatch_wheel outline 0.60 against code build 0.45; eight objects "every Pro take failed the shape check"; keyboard paint dE 33.1) and sample-measures.json; run by score/stages/props/compare.py, 2026-10-12. Prop route first: score/stages/props/CLAUDE.md (owner 2026-10-12); likeness.py (eight outlines, OUTLINE_LEAST = 0.50); unverified seeds: CONTEXT.md. -->


![Generation first on four hub objects. Columns: close-up, generated model, code build, final model. The hatch wheel's generated model passes its outline check at 0.60 where its code build fails at 0.45; the pliers pass at 0.81; every close-up of the screwdriver failed, so its code build carries it; the keyboard fails both ways (paint ΔE 33.1; code build too thin and out of proportion) and needs a new builder. Generated models are split into library surfaces, not baked.](figures/fig-k2.jpg){width=72%}

<!-- Figure 2: demo K2, paper/evidence/demos/K2.txt; numbers from paper/evidence/compare-hub/table.json and sample-measures.json; renders EUR 0.19 (cloud ledger, tickets "demo-turntables"). -->

# Stages and their gates

## Surfaces: the finish map

Models give shape only; every part takes one surface from a shared library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette and worn only where wear has a cause (Appendix D). Gemini 3.1 Pro [@gemini31pro] lists the close-up's finishes and names a library surface for each. Nano Banana Pro draws the close-up again with one flat colour per finish, up to three times until the map fits the close-up's outline, then draws unlit renders of the raw model's sides and back against it. SegviGen [@li2026segvigen] splits the mesh guided by the close-up's map, every map votes on the faces its view sees, and a part whose second finish holds a fifth of it fails. Each part is painted from its library surface and baked, never in the picture's colours, which gave every piece its own rust and stains (Appendix A).

The bake is checked against the close-up. A finish's surface must lie within ΔE 32 of its colour there, else a nearer surface of its family is taken or a new one is proposed to the creator, and the part fails by name. From the greenhouse's water tank, which the creator found baked as three near greys and tipped, came two checks: a bake fails when it darkens a finish the close-up shows lighter, or turns all surfaces into one grey; and short legs are stretched onto one level plane, a foot over 3 cm off the floor failing. Dirt follows the close-up.

<!-- score/stages/surfaces: ROWS (inputs, turntable, lists, maps, names, segvigen, parts, paint, bake, check); finish_ask.py LIST_MODEL gemini-3.1-pro-preview, MAP_MODEL gemini-3-pro-image; finish_rows.py SEEDS (1, 2, 3); finish_maps.py IOU_LEAST 0.85; finish_parts.py FRONT_VOTE 2.0, MIX_SHARE 0.2, COLOUR_DELTA_E 32.0; bake_check.py BAKE_DELTA_E 20.0, CLOSE_UP_DELTA_E 32.0, order_faults, one_look_faults, judge_stance (STANCE_GAP 0.03), OWN_COLOUR; place_line.py measured_dirt; tools/props/library/feet.py; registry.py. The water tank: docs/bible.md architecture/experimental, the surface stage's method (2026-10-12). Finish-map method chosen by the owner on 2026-10-12. -->

## Resting

Loose objects are dropped onto the made ground in a physics simulation; one that would turn more than 15 degrees or drift more than 30 cm is a resting fault of the layout and keeps its laid pose. The settle stage lays where each object comes to rest as a layer (held objects snapped onto their holders, a stack onto one support, an object that would rest worse kept as laid), gated on `rested` and `resting` (no fault that appears with the layer and not without it).

<!-- tools/usd/settle.py TURN_MOST 15, DRIFT_MOST 0.3; score/stages/settling (held.py, onto_one_support, kept_where_worse; gates rested, resting); SETTLED in score/stages/__init__.py. -->

## Light

Lamp strengths are measured, never copied from the source game. The light layer places live lamps from the scene record, with the sky, the sun and the Earth. One paid render per place gives every lamp its own Cycles light group on the place's views; because light adds up, the look at any strengths is mixed from these passes without rendering again, and a free sweep chooses the scale that brings the place's brightness within 1.5 times its concept's, halving any lamp that turns what it lights white. Outdoors the suns are swept after the lamps. A lamp whose fixture stops 90 percent of its rays moves out of it, and one behind a clear lens stands just outside, as Cycles passes no light through a glowing lens.

<!-- score/stages/light: mix.py (BRIGHT_WITHIN 1.5, BLOWN_MOST 0.2, HALVINGS 5), layer.py lamps_through_fixtures (ENCLOSED 0.9; commits a564c54, f8ee407), sun_lamps (4ab0827), gates in __init__.py; live lamps and the baked per-lamp plan: score/stages/light/CLAUDE.md. -->

## Motion, effects and sound

**Motion.** Each mover (a path, a hinge, a spin, a rail, a turn, a climb) has its kind's speed range cited from real machines, gated on `clear` (no mover within 3 cm of a still thing or another mover, read every quarter second), `speeds`, `loops`, `grounded` and `covered` (every still prim of a moving kind says why). **Effects** are emitters measured against real footage (photographs of lift-offs, rover films of Martian dust devils), gated on `attached`, `footage`, `light` (the flame lights the pad at least twice as brightly as the place's lamps) and `outside` (no open-sky particle inside a room). **Sound:** every source a place names (room tones, objects, motions, each surface's steps) gets the world's picked file or the best of eight MOSS-SoundEffect [@moss2026] takes of its brief, gated on `sources`, `level`, `likeness` (CLAP [@wu2022clap] score at least 0.30, the tenth percentile of the world's picks) and `no freesound`.

<!-- Motion: score/stages/motion, tools/usd/movers.py, data/checks/motion.json (speed ranges, cited), REACH_MOST 0.03. Effects: score/stages/effects (LIGHT_OVER 2.0), data/effects/*.json, sources in docs/bible.md architecture/experimental. Sound: score/stages/sound (gates.py CLAP_FLOOR 0.30, 8 takes a brief). -->

## People

People are made like props: a FLUX.2 klein [@flux2klein] close-up in SOMA-X's bind pose, built by Pixal3D, painted by the surface line, over SOMA-X's body fitted just inside (Gauss-Newton, 24 shape numbers), whose skin weights each look point takes from its closest triangle; Kimodo's clips [@rempe2026kimodo], from sentences, move it. The **shell gate** passes a look when 99 percent of its soft points lie within 5 cm of the body, its worst point recorded. Hard parts ride one joint, belts are cloth, each clip gets its own verdict (tucks, hard parts stretched, cloth or body through cloth) and casts use only passing clips; a far-only look is judged on its far body (Appendix B). **Casts:** SAM 3 [@carion2025sam3] finds the concept's figures, a judge tells people from pictures, reflections and empty suits, and casts are gated on `counted`, `standing`, `clear`, `made` and `drapes`; no crowd copy fills a tenth of a view's height.

<!-- score/stages/people_bodies/bodies.py (FITTED 24, Gauss-Newton; SHELL_SHARE 0.99, OFFSET_MOST 0.05), tools/characters/maker/prop_build.py rigid_joint, CLOTH_WORDS; clips.py; far.py; tools/characters/maker/outline.py; data/people/colours.json; score/stages/cast (gates, FAR_SHARE 0.10), concept_people, layer.py. Commits 0d6a28a, 4ff0a0c, e80f07d, 45af7ec, 530316b, d045948. -->

## Completion

A place is complete when its gate passes on its final assembly: every row made or dropped with a reason, nothing unmade, no placeholder or resting fault, the creator's picks shown, every layer and shown place present, nothing from the source game. **Named gaps.** A fault the creator decides to ship with today is written down as a named gap: who decided, when, why, the objects and their measured faults. It moves only those objects' faults from the gate where they arise to the completion gate, which fails the place by name with the numbers; any other fault still stops the line, and the gate is never loosened. A cast's person with no accepted body is a named gap the same way. A hook stops an agent claiming a place is done while its gate fails: agents judging their own scenes agree with a measured geometry score only 45.8 percent of the time [@li2026lego].

<!-- Named gaps: score/stages/gaps.py, data/checks/gaps/<place>.json (commits b529601e, 504e6333, de405faf, e3c64f45); people: commit d5a84e67. tools/usd/complete.py CHECKS; tools/usd/contents.py JUDGES (people, effects, motion, crops, likeness, painted, light, sound, neighbours, game, waiting); score/stages/complete; .claude/hooks/completion_guard.py. LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. -->

## Budget and ledgers

Machines and Google calls write ledger lines with their node's ticket; the month's spend is the higher of ledgers and bill, which caught misses: EUR 1,554 billed against EUR 1,387 in the cloud ledger on 12 October 2026, and EUR 549 billed by Google for a day the earlier ledger put at EUR 30. Over 13.8 hours of world 1's run the ledgers hold EUR 117.45 of machines and EUR 34.19 of Google calls, most for painting (EUR 37.61), the finish maps (EUR 26.59), the people's bodies (EUR 16.09) and the light passes (EUR 10.17).

**Forecast.** Before a paid piece runs, its estimate is written down with the measured unit cost it rests on (the ledgers' medians per node, model or picture); after it, the ledger's actual. The projected total for the month is reported against a hard stop the creator sets. The record shows which estimates to trust: measured unit costs held (22 close-ups for the ship estimated at EUR 3.10 to 6.20, actual 3.50; seven box checks 1.75, actual 2.19), while the runner's flat table figure overstated work it could carry over (the prologue's surfaces and light, EUR 101.50 in the table, cost 0.86).

<!-- paper/evidence/cloud/forecast-2026-10-14.txt (ESTIMATE vs ACTUAL rows: prologue surfaces+light, ship close-ups 22 made pieces, ship machines-boxes x7; the hard stop and the method in its first lines). tools/props/cloud/CLAUDE.md (bill EUR 1,554 vs ledger 1,387 on 2026-10-12; Google EUR 549 vs 30 on 2026-10-11; google_spend started and finished lines); score/adapters/compute month_refusal. Per stage: paper/evidence/cloud/stage-euros-2026-10-13.txt (ledger lines with a runner ticket, 2026-10-12T19:06Z to 2026-10-13T08:54Z). -->

# Evidence

Four worlds are planned; world 1's 18 places are judged once their layers stand accepted.

**People.** Scored on what is drawn, no clip of any look is clean (Table 2). Takes in a wider A-pose crossed less at the bind and more in motion (10,610 visible crossings on the player's clips against 4,078), with no clip clean in either pose. People therefore ship as named gaps: the characters layer lays the people whose bodies stand accepted, and the completion gate fails every missing one by name.

<!-- paper/evidence/characters/people-2026-10-13.txt section 9 (wider pose), commit 3ba8be83; issue #5; named people: commit d5a84e67. -->

**Table 2.** People, 13 October (experimental, Section 3.5): usable clips of 19 per look by the gate as built, on drawn surfaces only, and as one piece on what cameras see. Faults and fixes: Appendix B.

| Look | Body gates | Gate | Visible | Cameras, one piece |
|---|---|---|---|---|
| Player (work) | pass | 5 | 0 | 0 |
| Bram (work) | pass | 5 | 0 | not run |
| Sefa (work) | pass | 0 | 0 | not run |
| Nev (work) | pass | 0 | 0 | not run |
| Kit, average man (olive) | fail: triangles | 0 | not run | not run |
| Player, wider pose (work) | fail: triangles | 0 | not run | 0 |
| Kit, average man, wider pose (olive) | fail: shell | 0 | not run | 0 |

<!-- paper/evidence/characters/people-2026-10-13.txt (sections 1-9: gate verdicts per look and clip, bind tucks, visible-only re-score, one-piece bind, camera rule, offset clamp, fold weights and dual quaternions, AAOS joint ranges, wider-pose takes). Measured with numpy on the stored bodies; no runs. Issue #5. -->


**Table 3.** Named gaps on 15 October: what world 1 ships without, failed by name in the completion gate or left out of this paper.

| Gap | Where | Why, and who decided | Next |
|---|---|---|---|
| People with no accepted body | every cast | no clip clean on what is drawn (Table 2); the creator, 13 Oct | a fix to the take's pose and binding |
| The ship, code-built | hangar (12 pieces) | no made model yet; the creator, 14 Oct | the made ship, from the plan of Figure 1 |
| Pieces that do not rest | wreck (5) | the settle drops models from before their bake; the overseer, 14 Oct | the settle fix |
| A foot off the floor | camp grounds' crane, greenhouse's seed tray | the level rule uses 1 percent, not 3 cm; the overseer, 14 Oct | the same fix |
| Paint or bake off the close-up | garage (4) | library surfaces held until next month; the overseer, 14 Oct | new library surfaces |
| Results per place, film, place pictures | all | not made by this draft | after the completion gates |
| Physics in an engine | one room | no engine adapter | an adapter |
| Worlds 2 to 4 | | not started | |

<!-- data/checks/gaps/{hangar,wreck,campgrounds,greenhouse,garage}.json (decided, reason, objects); people: commit d5a84e67; unmade demos: the demo shortlist of 14 Oct (K1, K3 to K6, K8, K9 not made by this draft). The overseer is the coding-agent session that guards the run under the creator's rules (CONTEXT.md). -->

**Agent tools.** With them an agent used about half the output and cost on two of three places; on the third it left more faults; one run each (Appendix E).

<!-- paper/evidence/agent-tools-bench/analysis.json; Table E1. -->

# Limitations, future work and conclusion

One creator judges; he accepted the hub before the runner. Closed models (Nano Banana Pro, Gemini 3.1 Pro) may change or go. Hard belts failed deep bends; light is live, measured on earlier layouts; objects are not interactive. Next: three worlds, an engine adapter, interaction, baked lamps, open models, locked parts, LEGO-Bench [@li2026lego]. In short, SCORE keeps, keys and judges every stage's output, so a fault is fixed where it happens; completed places will show if it holds.

<!-- Belt and clips: commits 45af7ec, 530316b, e80f07d; issue #5. Light: score/stages/light/CLAUDE.md. Physics: score/stages/physics. Closed models: score/stages/props/CLAUDE.md (close-ups by Nano Banana Pro), finish_ask.py. Hub accepted: Appendix A. -->


# References {-}

::: {#refs}
:::

# Appendix {-}

```{=latex}
\appendix
```

# The hub in six rounds

The surface library, one model per real-world object and the straightness check came out of six rounds of work on the hub on 6 and 7 October 2026, each answering the creator's verdict on the round before (Table A1). In the first two rounds, he chose between the old and the new method side by side from the same cameras.

**Table A1.** The hub's six rounds. Cost is given as rented GPU time in euros and picture-model calls in dollars. Frame time is the mean frame time on an RTX 5080, in the night scene, at 1600×900.

| Round | Change | Creator's verdict | Cost | Frame time |
|--------------|--------------------------------|--------------------------------|---------|------------|
| 1, two walls, A/B | surface library, routing by shape, room checks | chose the new method ("Y looks much cleaner") | €0.88 | 7.81 ms vs 7.53 |
| 2, two walls, A/B | 71-variant library, shared texture sets, roof check | chose the new method again | €1.70 | 8.05 ms vs 8.24 |
| 3, whole room | all stages end to end, 74 models | old models were still loaded; labels and floor fittings were wrong | €1.67 | 6.78 ms (old 9.22) |
| 4, whole room | detail through the pipeline, picture colours kept | "pretty much all of this became messy" | €8.50, $5.09 | 9.6 ms |
| 5, eight pieces, A/B | shape only from the pipeline, library surfaces, parts check | new method preferred for the door, notice board and porthole; three pieces still wrong | €0.21 | not run |
| 6, whole room | round 5 everywhere, one model per object, straightness check | "this looks amazing, I have no negative feedback" | €3.48, $1.07 | 5.6 ms |

<!-- R1: local R&D log progress-robust-exp.txt [A/B numbers], blind key, quote at "ROUND TWO". R2: [A/B round two], [spend round two]; session record 2026-10-06T16:52Z. R3: progress-robust-exp.txt round three and fix round. R4: progress-hub-r4.txt; #130 comment 2026-10-07T05:29; quote in brief job-hub-r5-test.txt. R5: progress-hub-r5.txt; verdict as relayed in handoffs/hub-r5.txt. R6: progress-hub-r5.txt ROUND SIX; #130 comments 2026-10-07T15:55 and 16:20. -->

Three findings shaped the method. First, deterministic checks catch what agents miss: in round one, the share of rays leaking out through walls and roof fell from 1.53 percent of 5,817 to zero, and the colour noise within surfaces from a median of 31.1 to 3.2 percent, but only walking through the loaded room showed 26 old models still in it, which became the made-only check. Second, generated pieces that kept their pictures' colours made the room inconsistent, so surfaces come only from the library. Third, generated composite objects melted their parts together, and generated boxes leaned (one locker by 13 degrees), which led to one model per real-world object and to the straightness check. By round six the room used 0.45 million triangles, against 1.96 million in round four, and 187 MB on disk, against 487 MB.

<!-- Numbers: progress-robust-exp.txt [A/B numbers] and round three fix round; 2099 docs/bible.md item 11 (locker); #130 comment 2026-10-07T15:55 (round six vs four). -->


# Check details

- **Room checks** cast rays to find light leaking out through walls and roof, find pieces in front of a real opening and roof and wall fittings more than 3 cm off their surface or turned more than 5 degrees from it, and count pieces, triangles and lamps against the room's budget.
- **Door check:** every door must stand in a wall or partition that fully separates its two sides, tested by walking a grid from one side to the other.
- **Model check:** every model must have walls at least 3 mm thick. A generated box fails if one of its sides tilts more than 2 degrees or is warped. Making a generated model solid stops if its bounding box grows more than 3 percent.
- **Likeness gate:** a made model's outline from eight sides must overlap its close-up's by at least 0.50, a least set on the hub's twelve accepted generated models with a margin of 0.05, and its DINOv2 [@oquab2023dinov2] similarity must reach a least set the same way; without that calibration the gate answers unknown.
- **Finish maps:** a close-up's map passes when its outline overlaps the close-up's by at least 0.85 and it uses every listed finish; a part whose second finish holds 20 percent of its voted area mixes finishes and fails.
- **Bake check:** each baked part within ΔE 20 (CIE76) of its surface's colour and within ΔE 32 of its close-up's; lightness order fails when the close-up shows one surface more than 10 L\* lighter and the bake makes it more than 3 L\* darker; one look fails when no two near-neutral surfaces bake far enough apart for a viewer to tell at the place's view distance, while the close-up shows them more than ΔE 24 apart. What a viewer tells is measured, not set: Stone, Szafir and Setlur measured the CIELAB difference half of their viewers see between two colours s degrees wide, per axis ND(50, s) = C + K/s, with (C, K) = (5.08, 0.75) for L\*, (5.34, 1.54) for a\* and (5.35, 2.87) for b\* on sizes 1/3 to 6 degrees [@stone2014size]; two surfaces are told apart when their difference, each axis over its ND, is 1 or more. A surface's size is its model's middle size times the root of its area share, seen from the place's nearest view. This replaced a fixed ΔE 12, which failed the wreck's access cover on a 9.3 L\* step between its steel and its scorched white that its owner sees (11.3 degrees from the nearest view; half of viewers see 5.2 L\* at that size); <!-- ND(50) constants: Stone et al. 2014, Table 3; sizes: score/stages/surfaces/bake_check.py seen_degrees on data/kit/wreck.json and data/scene/wreck.json; the cover's bake: its surfaces-check record, test in score/stages/surfaces/surfaces_test.py --> a quadrant of a standing model's base more than 3 cm off the floor fails. Glass, screens, lamps and print are judged by their own colour and left out of the order.
- **Settling and resting check:** an object that would turn more than 15 degrees or drift more than 30 cm when dropped keeps its laid pose and is marked as not resting; small debris, with no side over 1.4 m, may turn freely and drift up to 1 m. Hung objects are exempt by their inventory anchor, and fixed objects are not judged for tipping. The triage fails a foot off its support and an up axis leaning more than 3 degrees.
- **Light:** the place's median brightness within 1.5 times its concept's and every view within 2.5 times; a lamp is blown when over 20 percent of the pixels where it gives at least half the light are white, and unlit when it gives less than 0.001 percent of every view's light.
- **Motion:** no mover within 3 cm of a still thing or another mover, read every 0.25 s; rounds join within 1 mm; speeds within each kind's cited range.
- **Sound:** CLAP score against the brief at least 0.30, the tenth percentile of 55 of the world's picks; a take no more than 0.5 s longer than its brief.
- **People:** the shell gate passes a look when 99 percent of its soft points lie within 5 cm of the fitted body; the worst point and its joint are recorded. A clip is usable when no frame tucks more than 5 mm, no hard part stretches past 1.2 times its bind length, cloth crosses cloth no more than in the earlier body's same clip, and no part's edges pass through cloth deeper than 3 mm more often than at the bind. A far-only look is judged on its joins, likeness and the far body's triangles (at most 1,220); the near outfit's triangles and shell offset are recorded, not gating. The A-pose outline is judged against the finished Pixal3D take the build starts from; the take's own loss against the raw model is recorded apart. A crowd copy stands only where it fills under a tenth of every view's height.
- **Worse than accepted:** a measure counts as worse only when it moves the wrong way by at least its tolerance, the smallest change a viewer could see: one more fault for a count; 0.02 of full scale for lightness on 0 to 1 (a halo, fill, beam or haze wash), and 5 of 255 levels for a colour gap, the step a viewer notices between two pictures; 0.05 for a brightness ratio; one percent of the picture for a share of it; a twentieth of the Earth's lit disc; 5 mm for a length. A score no viewer reads directly, such as a likeness score, is worse by any move. Tolerances decide only whether an output waits for the creator; a check that fails still fails.
- **The creator's accept carried forward:** when he accepts a worse output, his accept records what he allowed, each measure's value before and after. A later output that passes every gate and is no worse than the output he took, within the tolerances, is accepted by the runner with his accept named; a move beyond it still waits for him.
- **What the creator acts on:** he rejects, accepts or waives only an output he has seen on its review page. This is his rule; the commands do not yet check that the page was opened.
- **People seen by the cameras (experimental):** a clip's crossings of body through cloth are counted only where a camera that will show the person can see them: the place's views at the person's cast spot, and a close front and three-quarter view. Crossings no camera sees are recorded, not counted against the clip. So far this is a measure on the stored bodies (Section 3.5); the per-clip gate does not use it yet.
- **Completion gate:** the requirements given in Section 3.6, each with its result tied to a fingerprint of the stage's files and inputs; a result made on another stage counts as unknown. The placeholder check judges every mesh a code builder draws, and only the shell builders pass unnamed.

**People results in detail (experimental, Section 3.5).** The body gates are joins, outline, likeness, triangles and shell. Nev's and Sefa's boot tuck bands lie 9 to 11 mm outside the trouser leg at the bind pose. Scored on drawn surfaces only, no clip of any look is usable: skin seams open and settled cloth crosses itself. Bound as one closed mesh, the player's limbs sink into chest and hips, 87 to 563 crossing points visible from the places' cameras and close views per clip, the armpit surface stretching between arm and chest. The boot tuck bands run through every clip of Nev and Sefa before any motion. Where hair or cloth meets the head or hand skin the two sides are weighted differently and open as the joints move (cloth seams never open), and the settled cloth crosses itself beyond the bind; openings over 10 cm on three looks are not yet confirmed by a render. Binding the take as one closed mesh removes the openings. Pushing points out of the look's own volume, limiting the offset from SOMA-X at the armpits and inner thighs, fold-centred weights and dual-quaternion skinning each left the visible crossings the same or higher. A close-up drawn in a wider A-pose (arms 45 degrees below level, feet 35 cm apart) gives a take with fewer crossings at the bind (the player's 678 against 772) but more in motion, as the clips bring the arms further down: 10,610 visible crossings against 4,078 over the player's 19 clips, and no clip clean in either pose. The clips' joint angles stay within the normal human ranges of the American Academy of Orthopaedic Surgeons, except hip extension of 24 and 27 degrees (limit 20) in two clips. <!-- paper/evidence/characters/people-2026-10-13.txt sections 1-9; issue #5. -->

**Decisions recorded in these checks.** Three people's gates are decisions of the captain, the agent session that runs world 1, taken on 12 and 13 October 2026 under the creator's rules and open to his reversal. (1) The shell gate counts 99 percent of the soft points rather than every point, with the worst point recorded: the points beyond it were loose cloth edges (cuffs, hems, caps), which no part label names, so they could not be given a joint of their own by label. (2) A look seen only far away is judged on what is drawn far away, not on the near outfit it was made from. (3) The A-pose outline is judged against the finished take, not the raw model, so the take's own loss is not charged to the build. Earlier, the full-body cut (which looks get bodies in full and which only far ones) was set by the people's share of the budget.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). Likeness: score/stages/props/likeness.py (OUTLINE_LEAST 0.50), CLAUDE.md. Finish maps and bake: score/stages/surfaces/finish_maps.py, finish_parts.py, bake_check.py. Settling, resting and triage: tools/usd/settle.py, resting.py, triage.py (LEAN_MOST 3.0). Light: score/stages/light/mix.py (UNLIT_SHARE 0.00001). Motion: score/stages/motion (REACH_MOST 0.03, SEAM_MOST 0.001). Sound: score/stages/sound/gates.py. People: score/stages/people_bodies/bodies.py, clips.py, far.py (FAR_TRIANGLES 1220); tools/characters/maker/outline.py; score/stages/cast (FAR_SHARE 0.10). Decisions: commits 4ff0a0c (shell gate, outline), e80f07d (far-only), 9821002 and 353294e (full-body cut); issue #5, comment 6139504056. Placeholder check widened to every code-builder mesh: score 6364971. Carried accept: score/review/__init__.py (owners_allowance, within_owners_accept, allowed_moves), commit 0a6d0e4. The page rule: captain's brief of 2026-10-13; score/review/__main__.py has no check of it. Camera measure: paper/evidence/characters/people-2026-10-13.txt sections 5 and 7; score/stages/people_bodies/clips.py does not read cameras. Tolerances: score/review/__init__.py (TOLERANCES, COUNT_STEP, LIGHTNESS_STEP 0.02, LEVEL_STEP 5.0, RATIO_STEP 0.05, PICTURE_SHARE_STEP 0.01, DISC_SHARE_STEP 0.05, LENGTH_STEP 0.005). -->

# Models and licences

Every model in the framework must allow commercial use of its output (Table C1); we read each licence for its clauses on commercial use. Candidates were dropped under this rule, among them NVIDIA's Lyra 2.0 (weights for internal research only), Hunyuan3D 2.1 (licence does not apply in the European Union) and GarmentCode's fork of NVIDIA Warp (non-commercial research only), which Newton's cloth solver on upstream Warp replaced; Blender's cloth simulation [@blender] is kept as a second route. The one open doubt is the face LoRA, whose training data is not disclosed.

**Table C1.** Models in the framework.

| Model | Role | Licence |
|---|---|---|
| Nano Banana Pro [@nanobananapro] | concepts, close-ups on the prop route and those the open model fails, ground skins | paid API |
| Nano Banana Pro [@nanobananapro] | finish maps: the close-up drawn again with one flat colour per finish | paid API |
| Gemini 3.1 Pro [@gemini31pro] | each model's finishes listed on its close-up, and their library surfaces named | paid API |
| Qwen-Image-Edit-2511 [@qwenimageedit] | close-ups, first (before the prop route) | Apache-2.0 |
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
| MoGe-2 [@wang2025moge2], SAM 3 [@carion2025sam3] | measuring and finding objects in pictures; counting people and crops on the concepts | MIT; SAM Licence |
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

The close-ups' shape check was tuned on 40 close-ups that four open picture models drew of the lab's ten objects, each scored by hand, and on Nano Banana Pro's ten pictures of the same objects. With the majority of three sampled answers, the check agreed with the hand score on 29 of the 40, passed all ten of the closed model's pictures and two marginal ones, passed none scored wrong or failed, and failed nine that were good or usable. A single answer at temperature zero was rejected: asked 51 questions twice in one batch, it changed 7 verdicts. On the lab, 7 of the closed model's first pictures drew the room or dimension lines; all 7 passed when redrawn from the crop alone.

**Table C2.** The close-up stage on world 1. Cloud is rented card time in euros; the closed model's pictures are in dollars.

| Run | Close-ups | Open model accepted | Closed model accepted | Left for the creator | Cloud | Closed model |
|---|---|---|---|---|---|---|
| Lab, 22 rows (earlier check: one answer) | 22 | 8 | 14 | 0 | €4.12 | $2.81 |
| World 1's remaining rows (three places) | 17 | 0 | 10 | 7 | €3.06 | $4.02 |

<!-- Tuning: progress-openpics.txt 18:53 (vote: 29/40 agree, 0 wrong/failed passed, 2 marginal passed, 9 wrong fails; Pro 10/10), greedy rejected 17:56 (7/51 differed). Lab: progress-openpics.txt 17:35 (8 Qwen, 14 Pro, 7 Pro first takes failed for the room or dimension lines, all crop-only retakes passed, EUR 4.12 cloud, $2.81 Pro). World 1: progress-world1-score.txt 18:55 (workshop, greenhouse, campgrounds; 17 rows) and 20:12 (10/17 accepted, all by Pro, Qwen 0/17, 7 for review, EUR 3.06, Pro $4.02). -->

The picture-to-3D step, the part splitting, the surface bakes, the sound generation, all checks and the assembly run automatically. Coding agents (Claude Code [@claudecode]) write the plans, the inventories and every code builder; in the hub's final round, 86 of its 98 models were built in code. Some steps were still done by hand: some generated objects were turned to face the right way by eye, and a few labels were placed by hand before a rule took over that job. The concepts and the verdicts are the creator's own choices.

<!-- 86 of 98: 2099 docs/bible.md item 11. Hand steps: session record 2026-10-07T16:33Z. Licences: progress-robust-exp.txt [0 sources], [splitter]; progress-worldstep.txt STEP 1. Characters' licences: the characters' licence check of job characters-full, 2026-10-09 (progress-characters-full.txt 12:56, the coordinator's brief to the paper agent), recorded in tools/props/cloud/characters_setup.sh and tools/characters/maker/CLAUDE.md; Hugging Face licence tags of FLUX.2-klein-base-4B, refcontrol-FLUX.2-klein-4B-reference-depth-lora (apache-2.0) and VAST-AI/UniRig (mit), read 2026-10-09; SAM3DBody-cpp LICENSE (MIT). -->


# The surface library

The surface library holds families of variants, among them painted, steel, aluminium, rubber, plastic, cable, fabric, composite, glass, screen, light, print, wood, ground, foil, water, skin and hair. After the hub's second round it held 71 variants made from 14 ProcFunc recipes; it now holds 369 variants in 26 families made from 22 recipes. Each variant is a recipe with settings, takes its colours only from the palette, and is baked into base-colour, metal-roughness and normal maps at a texture density that depends on how close the player can get. Wear has three levels and comes from causes: edges, and kicks within 32 cm of the floor that a piece stands on. A surface the finish-map route proposes enters an append-only registry and joins the library only when the creator accepts it.

<!-- 71/14: progress-robust-exp.txt round two. 369/26/22: data/library/materials.json at 4c5365e (families' variants, recipes). Kick wear 32 cm: 2099 docs/bible.md item 11. Registry: score/stages/surfaces/registry.py. -->

# With and without the agent tools

The tools that check an agent's work were tested on three places of world 1: a room (the workshop, 814 objects), an outdoor place (the street, 1,198 objects) and a dense room (the hangar, 1,657 objects). They are the completion gate (Section 3.6); a triage of the resting check, which judges each object by what holds it up, read from its inventory row, and keeps only real faults [@tam2025sceneeval; @xia2026sage]; a pick lock, which refuses an export that would show anything but the model the creator picked for a row; and a render-and-compare, which lists the objects least like their close-ups by DINOv2 similarity [@oquab2023dinov2]. In both arms, the same agent (Claude Opus 5.5 in Claude Code, headless) started from the same exported stage and inventory and was asked to make the place as complete as it could in about 50 minutes, through its layout data only; one arm had the framework from before these tools. Each arm ran once, so Table E1 shows what happened, not an average.

**Table E1.** One session per arm and place. Faults are the resting triage's real faults left on the final stage, measured against the arm's own data; placeholders by the first placeholder check; rows are inventory rows with no object and no written reason. Agent cost is the session's model cost; cloud is its rented machines' cost.

| Place, arm | Faults, start → end | Placeholders | Rows missing | Min. | Agent cost | Output tokens | Cloud | Exports | Unknown gate calls |
|--------------------|---------|---------------|--------|------|-------|-------|-------|---------|------------|
| Workshop, without | 18 → 13 | 0 → 0 | 1 → 0 | 36 | $2.26 | 30.4k | €0.85 | 7 | not used |
| Workshop, with | 18 → 0 | 0 → 0 | 1 → 0 | 26 | $1.42 | 14.3k | €0.85 | 2 | 2 of 4 |
| Street, without | 11 → 0 | 0 → 0 | 0 → 0 | 38 | $2.40 | 30.0k | €0.32 | 9 | not used |
| Street, with | 12 → 0 | 0 → 0 | 0 → 0 | 39 | $1.21 | 10.4k | €0.76 | 1 | 0 of 5 |
| Hangar, without | 14 → 4 | 5 → 0 | 0 → 0 | 47 | $2.01 | 26.6k | €0.00 | 7 | not used |
| Hangar, with | 14 → 9 | 5 → 0 | 0 → 0 | 32 | $2.34 | 29.1k | €0.64 | 5 | 3 of 6 |

The tools made building cheaper more often than they made the scene better. On the workshop and the street, the arm with the tools used about half the agent's output and cost, and exported the stage once or twice instead of seven to nine times, because the triage named the few real faults among hundreds of alarms. On the workshop, 13 of its 18 faults were cleared by writing into the inventory what holds a piece up, which the creator still has to confirm. On the hangar the arm without the tools left fewer faults: the arm with them spent its time replacing five placeholder slabs and trying the drop test, which failed on a room with no ground mesh (fixed after the run), and the nine faults it left are models with stray parts below their feet. No agent claimed a place was complete, so the gate's hook never had to refuse a claim. No row carries an owner's pick, so the pick lock was not tested.

<!-- Benchmark: paper/evidence/agent-tools-bench: analysis.json (written by the bench's analyse.py from each session's record and transcript), and per arm and place (on = with, off = without) measure-start.json, measure-end.json, measure-manual.json and session.json. Arms: without = score 672ddfd, with = ff44157 (both with ff44157's data for the three places); claude -p --model claude-opus-5-5, 2026-10-09. The street's start reads 11 and 12 because the two start measures read the inventory from different checkouts; the stage was the same. The workshop's 13 cleared by data: 11 tool-board tools set to hanging, two arm monitors fixed (session report). -->
