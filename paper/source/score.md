---
title: "SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments"
author:
  - "J.P. Kardolus, Babon Innovations B.V., Utrecht, The Netherlands"
date: "Working draft, 13 October 2026"
abstract: |
  Games, films and robot training need 3D worlds that are complete, editable and owned by the people who make them. World models and one-shot 3D generators can produce a convincing place from a sentence or a picture, but they give frames that no engine can open, or one fused scene without separate objects or clear rights. Studios have always built worlds in stages, from concept art and layout to modelling, surfacing, lighting, sound and review. We present SCORE, a world generation framework that keeps these stages and automates them with open vision foundation models, procedural tools and coding agents, while the creator chooses and reviews. Every stage is a node of one runner: its output is keyed on its inputs and its code, judged by gates that answer pass, fail or unknown, and accepted only when nothing got worse, so a fault is fixed in its own stage and only what follows it runs again. Paid steps are cleared against a month's budget read from the provider's own bill. Every model in the framework allows commercial use of its output, so the creator stays the author of the result. We describe the framework as built for its first world, the game world of 2099 with 18 places, and the measured gates of each of its layers: surfaces, resting, light, motion, effects, sound and people. Results per place are being gathered. Code and paper are available at https://github.com/Babon-Innovations-b-v/score (MIT license).
---

<!--
  Draft conventions (paper/CLAUDE.md).
  - Final paper's structure. Settled content is written in full; wherever final content will go,
    a gap box says what goes there and what it waits on.
  - Main text: the three contributions only (the staged framework, its stages and gates, the evidence),
    about 4 to 5 pages plus references while gaps are open. The appendix holds only the evidence
    behind a claim the main text makes.
  - Every number is read from a file named in a comment beside it.
  - Figures and tables follow the demo targets of 12 October 2026 (F1 to F11, T1, T2, the film): each is
    rendered from a place's final OpenUSD stage after its one assembly and completion check, never from an
    older render; until then it is a gap box.
  - The world step is one optional step; no result compares it with another model or judges it
    on its own, and its output is credited "Generated using World Labs".
-->

```{=latex}
\makeatletter\def\fps@figure{t}\makeatother
```

::: gap
**Gap: Figure 1, four worlds.** World 1's panel: the square (the prologue on Earth), the hub (the Moon base) and the Mars camp, each concept beside its finished stage rendered from the concept's own camera; worlds 2 to 4 shown as not started. It waits on those three places passing their completion gate on their final assembly; the square and the camp wait on their people's bodies.
:::

<!-- Demo target F1. -->

# Introduction

Interactive 3D worlds are the raw material of games, film and embodied AI [@yang2024holodeck], and building one is expensive: every object has to be modelled, surfaced, placed, given collision, lit and given sound in one style, and the world has to stay editable. Generative models promise to take over much of this, but in GDC's 2026 survey 52 percent of game workers thought generative AI was hurting the industry [@gdc2026survey]; a tool for building worlds has to leave the result in the creator's hands.

World models generate a world as frames [@bruce2024genie; @genie3] that no engine can open. 3D world generators [@wang2025worldgen; @hyworld2] produce geometry, but mostly as one fused asset, from which separate objects are recovered after the fact [@hu2026worldact; @niu2026worldsculpt]. Both work in one shot, so a creator cannot find or change the step behind a fault. Procedural systems [@raistrick2023infinigen; @raistrick2024indoors] and coding agents that write scenes as programs [@hu2024scenecraft; @li2026rcwm; @guo2026worldclaw; @yin2026autoue] keep the world explicit, but rebuild a scene that already exists or draw their objects from a fixed library, and such agents judge their own geometry unreliably [@li2026lego]. Open vision foundation models [@oquab2023dinov2] now read shapes [@li2026pixal3d], masks [@carion2025sam3], depth [@wang2025moge2] and parts [@lin2025partcrafter] out of pictures, and a coding agent can connect them as tools; none of them provides one style across objects that different models made, which the field names as an open problem [@wu2026production; @yang2026flowscene].

Studios build worlds in stages, each with an output a person can check. SCORE keeps these stages and automates them with the models above, procedural tools and coding agents, while the creator chooses and reviews. Its worlds are **complete**: every object, surface, light and sound exists wherever the player looks. They are **owned**: every model in the framework allows commercial use of its output, so the creator stays the author, holding the full commercial rights. They are **responsive**: every object has real collision, mass and material. And they can be any kind of **environment**. To our knowledge, no other openly available world generation work joins vision foundation models into engine-ready scenes that are built from reference pictures, steered by a person's choices at each step, and made only with models that allow commercial use of their output.

<!-- "To our knowledge" claim and nearest exceptions: 2099 paper material/08-reframe.md, "The owner's position" (availability check of twelve systems, 2026-10-05); the repository is now public under MIT. Hand-off pattern: material/11-vision-foundation-models.md. -->

This paper makes three contributions:

- **The SCORE framework:** stages as nodes of one runner that keys, judges and accepts every output, over one canonical scene: a generated base under the creator's edit layer (Section 2).
- **Stages with measured gates** for every layer of a place: models, surfaces, resting, light, motion, effects, sound and people, and a completion gate over all of them (Section 3).
- **Evidence from a first world**, with its spend per stage read from the ledgers and the bill (Section 4).

# The framework

A world is a table of stages; world 1's has 95 rows. A **node** is one stage for one place (`assembly@hangar`) or for the whole world, and one runner makes, judges and accepts every node. The creator's picks (the concept of each place, the style, the references) are the inputs; from there everything runs without a typed yes, and the creator reviews.

<!-- 95 rows: len(score.stages.STAGES) at 4c5365e. Picks as inputs, no typed yes: the owner's answers of 2026-10-11 on issue #6 (design approved, decisions 1 to 3). -->

## Keys, gates and accepts

**Keys.** A node is made only when its key has no finish record. The key hashes the stage and place, a code version, the contracts of its output and inputs, its parameters, a seed derived from the world's, the pinned model images, every world file it reads and the accepted output of every node it reads. The code version hashes every source file the stage's make and gates import, walked through their imports; the runner and the renting code are left out, since they change what a run costs, not what it makes. A fault fixed in one stage moves the keys of that stage and of what follows it, and nothing else. Outputs are kept by content hash, never overwritten, each stamped with its schema in metres, seconds and degrees.

**Gates and accepts.** Each gate answers pass, fail or unknown, with measures and a reason; missing evidence is unknown, and unknown blocks like fail. The runner accepts an output by itself when every gate passed and it is no worse than the output accepted before: no answer dropped, no measure moved the wrong way, no gate went missing. Later nodes read only accepted outputs. The creator keeps four commands, from his own terminal: reject an accepted output (it moves back to the one before, and every node that read it is stale), accept a worse one with his reason, waive one gate for one key, and override the runner for one paid run. None is needed for a run. Agents are kept from them by a barrier, not a lock: the commands want a terminal, the store refuses the creator's records from any process an agent started, and a hook blocks the other routes.

**Spending and review.** A paid node is cleared only when every gate on its inputs passed and the month's ceiling has room for its estimate (Section 3.7); every place in the code that rents a machine or calls a paid model refuses without that ticket, and a run that would buy again more than EUR 5 of accepted outputs needs a written reason. Each node's review page is built from the store alone (its gates' answers and measures, who accepted it, the command that rejects it), and the creator reviews a place in a USD viewer on the store's copy of its accepted assembly; nothing is rendered for review.

<!-- Keys: score/graph/__init__.py (own_parts, worked_out_key, node_seed, code, usable), score/graph/_code.py (source_files, FRAMEWORK). Contracts and store: score/contracts, score/store. Gates: score/checks (judge, missing_evidence, overall, blocks, regressions). Accepts and the creator's commands: score/review/__init__.py (accept_automatically, accept, reject, waive), score/review/__main__.py (terminal check), score/store OWNER_AREAS, .claude/hooks/accept_guard.py. Clearance: score/adapters/compute/__init__.py (clearance, month_refusal, require_cleared). Re-buys: score/graph/rebuy.py LIMIT = 5.0. Review in the viewer, no renders: commits f63212c, 4c5365e. -->

::: gap
**Gap: Figure 2, the stages on the hub** (concept, plan, inventory, close-ups, a library surface at three wears, the assembled room), **and Figure 3, the greenhouse's review page.** They wait on the hub's and the greenhouse's one assembly passing its completion gate; the earlier hub figure predates the runner and is withdrawn.
:::

<!-- Demo targets F2 and F10. -->

## From concept to scene

**Inventory, plan and record.** A coding agent lists every visible element of the concept as an inventory row (kind, anchor, size, count) or drops it with a written reason; nothing is made or placed that is not a row. It draws a dimensioned plan, gated on `mapped` (every element of the concept a row, a door or a written drop; every door says where it leads). The scene record is written from the plan, inventory, made ground and sky, gated on `game-free` (nothing copied from the game the world came from), `plan-matched` (the shell within 5 cm of the plan), `openings` (every doorway onto a floor, no view into nothing) and `seed-matched` (every old entry matched or dropped with a reason).

**The canonical scene.** Every place is one OpenUSD stage [@openusd] in which each object carries its kind, transform, collision and the library surface of each part. Its layers lie in a fixed order, the creator's edit layer on top, then people, sound, light, motion, effects, crops, machines, settle, ground and the generated base, so an edit survives a regenerated base. Each place is assembled once, from every layer's accepted output; its `layers` gate answers unknown while a layer the place needs has none, and an old output never stands in.

<!-- Inventory rule: the owner's rule of 2026-10-08; issue #130, 2026-10-07T23:04. Plan and record: score/stages/scene_record (plan.py, gates.py: TOLERANCE = 0.05). Layer order: score/stages/assembly/__init__.py ORDER; layers gate: judge_layers; needs per place: data/checks/contents.json. -->

**Models, generation first.** Every object goes the prop route first: Nano Banana Pro [@nanobananapro] draws its close-up from its crop of the concept, Pixal3D [@li2026pixal3d] builds it, the surface stage paints it, and a free likeness gate compares its outline from eight sides with its close-up. Only an object whose measured checks fail is built by a code builder that a coding agent writes. This reverses the earlier parts check, which built a kind in code whenever its code build showed every part of the close-up (the creator's choice, 12 October 2026). Every real-world object stays one model: a console is a desk carrying separate monitors. Most of world 1's models predate the change and enter as unverified seeds, judged by the stages after them.

<!-- score/stages/props/CLAUDE.md (prop route first, owner 2026-10-12; likeness.py: eight outlines, OUTLINE_LEAST = 0.50); unverified seeds: CONTEXT.md, docs/bible.md architecture/components. -->

::: gap
**Gap: Figure 4, one scene, an edit kept** (the wreck from camera 1, with an edit that survives a regenerated base whose models were repainted), **and Figure 5, generation first** (four of the hub's objects, two generated and two falling back to code, with passes, euros and agent hours for both orders). Figure 4 waits on the wreck's surface check and assembly; the hub's comparison has run and waits on its record being published.
:::

<!-- Demo targets F5 and F3. -->

# Stages and their gates

## Surfaces: the finish map

Models give shape only; every part takes one surface from a shared library of rule-based surfaces, written as ProcFunc functions [@raistrick2026procfunc] on Infinigen's shaders [@raistrick2023infinigen], coloured from the place's palette and worn only where wear has a cause (Appendix D). Gemini 3.1 Pro [@gemini31pro] lists the close-up's finishes and names a library surface for each. Nano Banana Pro draws the close-up again with one flat colour per finish, up to three times until the map fits the close-up's outline, then draws unlit renders of the raw model's sides and back against that map. SegviGen [@li2026segvigen] splits the mesh guided by the close-up's map, every map votes on the faces its view sees, and a part whose second finish holds a fifth of it fails. Each part is painted from its library surface and baked; the picture's own colours are never kept, because when every piece kept them, every piece brought its own rust and stains (Appendix A).

The bake is checked against the close-up. A finish's surface must lie within ΔE 32 of its colour there, else a nearer surface of its family is taken or a new one is proposed to the creator, and the part fails by name. Two checks came from the greenhouse's water tank, which the creator found baked as three near greys and standing tipped: a bake fails when it turns a finish the close-up shows lighter into a darker one, or all its surfaces into one grey the close-up does not have; and a model on legs has its short legs stretched onto one level plane before its bake, a foot more than 3 cm off the floor failing. Each model is dirtied as much as its close-up shows, capped at its place's dirt.

<!-- score/stages/surfaces: ROWS (inputs, turntable, lists, maps, names, segvigen, parts, paint, bake, check); finish_ask.py LIST_MODEL gemini-3.1-pro-preview, MAP_MODEL gemini-3-pro-image; finish_rows.py SEEDS (1, 2, 3); finish_maps.py IOU_LEAST 0.85; finish_parts.py FRONT_VOTE 2.0, MIX_SHARE 0.2, COLOUR_DELTA_E 32.0; bake_check.py BAKE_DELTA_E 20.0, CLOSE_UP_DELTA_E 32.0, order_faults, one_look_faults, judge_stance (STANCE_GAP 0.03), OWN_COLOUR; place_line.py measured_dirt; tools/props/library/feet.py; registry.py. The water tank: docs/bible.md architecture/experimental, the surface stage's method (2026-10-12). Finish-map method chosen by the owner on 2026-10-12. -->

::: gap
**Gap: Figure 6, shape and surface apart.** Library swatches; the water tank's close-up, finish map, split and painted model; the hub's tool board with picture colours against library paint. It waits on the surface line at the greenhouse's and the hub's final assemblies.
:::

<!-- Demo target F4. -->

## Resting

Loose objects are dropped onto the made ground in a physics simulation; one that would turn more than 15 degrees or drift more than 30 cm is a resting fault of the layout and keeps its laid pose. The settle stage lays where each object comes to rest as a layer of its own (held objects snapped onto their holders, a stack onto one support, an object that would rest worse kept as laid). Its gates are `rested` and `resting` (no fault that appears with the layer and not without it).

<!-- tools/usd/settle.py TURN_MOST 15, DRIFT_MOST 0.3; score/stages/settling (held.py, onto_one_support, kept_where_worse; gates rested, resting); SETTLED in score/stages/__init__.py. -->

## Light

Lamp strengths are measured, never copied from the source game. The light layer places live lamps where the scene record puts them, with the sky, the sun and, seen from the Moon, the Earth. One paid render per place gives every lamp its own Cycles light group on the place's views; because light adds up, the look at any strengths is mixed from these passes without rendering again, and a free sweep chooses the scale that brings the place's brightness within 1.5 times its concept's, halving any lamp that turns what it lights white. Under the open sky the suns are swept after the lamps. A lamp is measured where it shines: one whose fixture stops 90 percent of its rays moves out of the fixture, and one behind a clear lens stands just outside it, since Cycles passes no light through a lens that also glows. Baking a pass per lamp, mixed live in the engine, is planned.

<!-- score/stages/light: mix.py (BRIGHT_WITHIN 1.5, BLOWN_MOST 0.2, HALVINGS 5), layer.py lamps_through_fixtures (ENCLOSED 0.9; commits a564c54, f8ee407), sun_lamps (4ab0827), gates in __init__.py; live lamps and the baked per-lamp plan: score/stages/light/CLAUDE.md. -->

## Motion, effects and sound

**Motion.** Each moving thing is a mover in the place's record (a path, a hinge, a spin, a rail, a turn, a climb) with its kind's speed range cited from real machines. The gates read the composed stage every quarter second: `clear` (no mover within 3 cm of a still thing or another mover), `speeds`, `loops`, `grounded` and `covered` (every prim of a moving kind that stays still says why).

**Effects** are emitters on a prim, measured against real footage: the launch's cloud and flame in rocket heights from photographs of real lift-offs, the camp's dust devils from rover films of Mars. The gates are `attached`, `footage` (every measure of the baked particles within the range read off footage), `light` (the flame lights the pad at least twice as brightly as the place's lamps) and `outside` (no open-sky particle inside a room).

**Sound.** Every source a place names (room tones, objects, motions, each surface's steps and impacts) gets the world's picked file or the best of eight MOSS-SoundEffect [@moss2026] takes of its brief, gated on `sources`, `level` (loudness, peak and length), `likeness` (CLAP [@wu2022clap] score at least 0.30, the tenth percentile of the world's picks) and `no freesound`.

<!-- Motion: score/stages/motion, tools/usd/movers.py, data/checks/motion.json (speed ranges, cited), REACH_MOST 0.03. Effects: score/stages/effects (LIGHT_OVER 2.0), data/effects/*.json, sources in docs/bible.md architecture/experimental. Sound: score/stages/sound (gates.py CLAP_FLOOR 0.30, 8 takes a brief). -->

::: gap
**Gap: Figure 7, light** (the old station with the Earth lit, a dark side away from the sun; one room at its swept strengths beside its concept), **and Figure 8, things that move** (the launch's lift-off, a rover leaving the garage with wheel dust, the camp's dust devil, an airlock cycle). They wait on those places' assemblies; the rover's drive waits on its painted model.
:::

<!-- Demo targets F8 and F7. -->

## People

People are made like props. A close-up of the dressed person in SOMA-X's bind pose, drawn by FLUX.2 klein [@flux2klein], is built by Pixal3D and painted by the surface line. SOMA-X's body is fitted just inside the look (Gauss-Newton on 24 shape numbers), and every point of the look takes the skin weights of its closest body triangle, so Kimodo's clips [@rempe2026kimodo], written from sentences, move it. The **shell gate** passes a look when 99 percent of its soft points lie within 5 cm of the body, its worst point recorded. Hard parts ride one joint each (hair, boots, bare hands, helmets), and belts are worn as cloth. Each clip gets its own verdict (tucks, hard parts stretched, cloth through cloth, body through cloth), and a cast uses only the clips that pass. A look seen only far away is judged on its far body, and a look's colour comes from the cast record's words (Appendix B).

**Casts.** SAM 3 [@carion2025sam3] finds the figures on a place's views, and a vision-language judge tells a person from a picture, a reflection or an empty suit. A cast is gated on `counted`, `standing`, `clear`, `made` and `drapes`; a crowd stands only where no copy fills a tenth of a view's height, and every person wears their look's accepted body, never a stand-in.

<!-- score/stages/people_bodies/bodies.py (FITTED 24, Gauss-Newton; SHELL_SHARE 0.99, OFFSET_MOST 0.05), tools/characters/maker/prop_build.py rigid_joint, CLOTH_WORDS; clips.py; far.py; tools/characters/maker/outline.py; data/people/colours.json; score/stages/cast (gates, FAR_SHARE 0.10), concept_people, layer.py. Commits 0d6a28a, 4ff0a0c, e80f07d, 45af7ec, 530316b, d045948. -->

::: gap
**Gap: Figure 9, people made like props.** The player from close-up to a walking frame, and the square's crowd of 10,000 with its front row. It waits on the people batch; the player's work suit had no usable clip because of its belt.
:::

<!-- Demo target F6. -->

## Completion

A place is complete when its completion gate passes on its final assembly: every inventory row has its object or a written reason; nothing visible is unmade or a code placeholder; no resting fault; every pick of the creator is the model shown; and the place holds what it needs: its cast in made looks, its effects and motions, its crops, every generated model held to its close-up and repainted, every lamp and room tone of its record, every place it shows, and nothing copied from the source game. Each answer is tied to a fingerprint of the stage; an answer made on another stage is unknown, and a hook refuses to end an agent's session that claims a place is done while its gate fails. Coding agents judging their own scenes agree with a measured score on geometry only 45.8 percent of the time [@li2026lego], so no agent's word completes a place.

<!-- tools/usd/complete.py CHECKS; tools/usd/contents.py JUDGES (people, effects, motion, crops, likeness, painted, light, sound, neighbours, game, waiting); score/stages/complete; .claude/hooks/completion_guard.py. LEGO-Anything 45.8%: arXiv 2609.36380 Sec. 5.1. -->

::: gap
**Gap: Figure 10, responsive.** A room in a physics engine, a dropped crate and a door reacting. The physics stage writes UsdPhysics collision, mass and friction and runs a Bullet trial, so far on the habitat only; until it passes, responsiveness is that trial.
:::

<!-- Demo target F11. score/stages/physics, tools/usd/physics.py, data/physics/. -->

## Budget and ledgers

Every rented machine writes a ledger line with its euros, and every call to Google's models writes a started line before the call and a priced line after it, so a call that never returns still counts. Each line carries the ticket of its node. The month's spend is the higher of the ledgers and the provider's bill, because the ledgers missed costs: on 12 October 2026 the month's cloud bill stood at EUR 1,554 against EUR 1,387 in the ledger (disks and addresses billed by the hour, storage, some card time), and on 11 October Google billed EUR 549 for a day in which the earlier ledger held EUR 30. Over 13.8 hours of world 1's run from the first ticketed line, the ledgers hold EUR 117.45 of rented machines and EUR 34.19 of Google's models; the largest stages were painting (EUR 37.61), the finish maps (EUR 26.59), the people's bodies (EUR 16.09) and the light passes (EUR 10.17).

<!-- tools/props/cloud/CLAUDE.md (bill EUR 1,554 vs ledger 1,387 on 2026-10-12; Google EUR 549 vs 30 on 2026-10-11; google_spend started and finished lines); score/adapters/compute month_refusal. Per stage: paper/evidence/cloud/stage-euros-2026-10-13.txt (ledger lines with a runner ticket, 2026-10-12T19:06Z to 2026-10-13T08:54Z). -->

# Evidence

We build four worlds with the same stages: the game world of 2099 (a prologue on Earth, a Moon base and a camp on Mars), a stylised underwater world, a simulation world for robots, and a third-person fantasy world. World 1 has 18 places, each its own line of the table, assembled and judged complete once, when every layer it needs stands accepted.

::: gap
**Gap: Table 1, results per place and stage, and the film.** Per place: inventory rows, models generated and built in code, the layers present, faults caught before and after spending, time, euros from Scaleway's and Google's bills, and the creator's verdict; and a four-minute walk through world 1 from each place's own cameras with its sound. They wait on each place's one assembly and completion gate.
:::

<!-- Demo targets T1 and the film; F9 is in Appendix F. -->

**With and without the agent tools.** On two of three places of world 1, an agent with the completion gate and its tools used about half the output and cost of one without them; on the third, the one without left fewer faults. Each arm ran once (Appendix E).

<!-- paper/evidence/agent-tools-bench/analysis.json; Table E1. -->

# Limitations

Every verdict is one creator's, and he accepted one place, the hub, before the runner existed. Closed, paid models draw the concepts, the prop route's close-ups and the finish maps (Nano Banana Pro) and list the finishes (Gemini 3.1 Pro); their limits set the pace, and they can change price or be retired, which limits reproducibility. People are not finished: belts worn as hard parts could not follow a deep forward bend. Light is live, not baked, and was measured on earlier layouts; objects are physical but not interactive.

<!-- Belt and clips: commits 45af7ec, 530316b, e80f07d; issue #5. Light: score/stages/light/CLAUDE.md. Physics: score/stages/physics. Closed models: score/stages/props/CLAUDE.md (close-ups by Nano Banana Pro), finish_ask.py. Hub accepted: Appendix A. -->

# Future work

The three further worlds; an engine adapter with mass and friction; interactable objects, which robotics needs; baked per-lamp light; open models for close-ups and finish maps; a shared library of locked, versioned parts that worlds reference instead of buying again; LEGO-Bench [@li2026lego]; and a measure of whether a place keeps one style.

# Conclusion

SCORE builds worlds from a creator's choices in stages whose outputs are kept, keyed and judged, so a fault is fixed where it happens and only what follows it runs again. On its first world, every layer of a place, from surfaces to light and people, has gates measured against the concept or real footage. Whether the framework holds across a whole world, and across kinds of worlds, is what world 1's completed places and the further worlds will show.


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
- **Bake check:** each baked part within ΔE 20 (CIE76) of its surface's colour and within ΔE 32 of its close-up's; lightness order fails when the close-up shows one surface more than 10 L\* lighter and the bake makes it more than 3 L\* darker; one look fails when every two surfaces bake within ΔE 12, near neutral, while the close-up shows them more than ΔE 24 apart; a quadrant of a standing model's base more than 3 cm off the floor fails. Glass, screens, lamps and print are judged by their own colour and left out of the order.
- **Settling and resting check:** an object that would turn more than 15 degrees or drift more than 30 cm when dropped keeps its laid pose and is marked as not resting; small debris, with no side over 1.4 m, may turn freely and drift up to 1 m. Hung objects are exempt by their inventory anchor, and fixed objects are not judged for tipping. The triage fails a foot off its support and an up axis leaning more than 3 degrees.
- **Light:** the place's median brightness within 1.5 times its concept's and every view within 2.5 times; a lamp is blown when over 20 percent of the pixels where it gives at least half the light are white, and unlit when it gives less than 0.001 percent of every view's light.
- **Motion:** no mover within 3 cm of a still thing or another mover, read every 0.25 s; rounds join within 1 mm; speeds within each kind's cited range.
- **Sound:** CLAP score against the brief at least 0.30, the tenth percentile of 55 of the world's picks; a take no more than 0.5 s longer than its brief.
- **People:** the shell gate passes a look when 99 percent of its soft points lie within 5 cm of the fitted body; the worst point and its joint are recorded. A clip is usable when no frame tucks more than 5 mm, no hard part stretches past 1.2 times its bind length, cloth crosses cloth no more than in the earlier body's same clip, and no part's edges pass through cloth deeper than 3 mm more often than at the bind. A far-only look is judged on its joins, likeness and the far body's triangles (at most 1,220); the near outfit's triangles and shell offset are recorded, not gating. The A-pose outline is judged against the finished Pixal3D take the build starts from; the take's own loss against the raw model is recorded apart. A crowd copy stands only where it fills under a tenth of every view's height.
- **Completion gate:** the requirements given in Section 3.6, each with its result tied to a fingerprint of the stage's files and inputs; a result made on another stage counts as unknown. The placeholder check judges every mesh a code builder draws, and only the shell builders pass unnamed.

**Decisions recorded in these checks.** Three people's gates are decisions of the captain, the agent session that runs world 1, taken on 12 and 13 October 2026 under the creator's rules and open to his reversal. (1) The shell gate counts 99 percent of the soft points rather than every point, with the worst point recorded: the points beyond it were loose cloth edges (cuffs, hems, caps), which no part label names, so they could not be given a joint of their own by label. (2) A look seen only far away is judged on what is drawn far away, not on the near outfit it was made from. (3) The A-pose outline is judged against the finished take, not the raw model, so the take's own loss is not charged to the build. Earlier, the full-body cut (which looks get bodies in full and which only far ones) was set by the people's share of the budget.

<!-- 2099 docs/bible.md items 11-12; progress-robust-exp.txt round two [surface check] and round three; progress-hub-r5.txt; #130 comment 2026-10-07T18:52 (door check). Likeness: score/stages/props/likeness.py (OUTLINE_LEAST 0.50), CLAUDE.md. Finish maps and bake: score/stages/surfaces/finish_maps.py, finish_parts.py, bake_check.py. Settling, resting and triage: tools/usd/settle.py, resting.py, triage.py (LEAN_MOST 3.0). Light: score/stages/light/mix.py (UNLIT_SHARE 0.00001). Motion: score/stages/motion (REACH_MOST 0.03, SEAM_MOST 0.001). Sound: score/stages/sound/gates.py. People: score/stages/people_bodies/bodies.py, clips.py, far.py (FAR_TRIANGLES 1220); tools/characters/maker/outline.py; score/stages/cast (FAR_SHARE 0.10). Decisions: commits 4ff0a0c (shell gate, outline), e80f07d (far-only), 9821002 and 353294e (full-body cut); issue #5, comment 6139504056. Placeholder check widened to every code-builder mesh: score 6364971. -->

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

# World 1, place by place

::: gap
**Gap: Figure F1, every place of world 1.** For each of the 18 places (the flat, stairwell, street, square and launch; the hub, lab, greenhouse, workshop, airlock, walkway tube, habitat, garage, hangar, wreck and old station; the camp and its grounds), the concept beside the final stage rendered from the concept's own camera. It waits on each place's one assembly passing its completion gate.
:::

<!-- Demo target F9. -->
