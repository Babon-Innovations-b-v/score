export const meta = {
  name: 'improve-env-round',
  description: 'One improve-env round: score every place still against its concept, find the shared causes, land one fix stream per cause',
  phases: [
    { title: 'Compare', detail: 'each place: still against concept, mismatches by cause' },
    { title: 'Causes', detail: 'shared causes across places, ranked, one fix stream per cause' },
    { title: 'Fix', detail: 'one agent per cause, own worktree, tested, pushed to main' },
  ],
}

// args: {environment, places: [..], stills, out, issue, round, model: 'fable', notes}; one fix stream per cause the round finds (owner, 2026-11-16)
const input = args
const MODEL = input.model || 'fable'

const CAUSES = 'SHELL (walls, floors, ceilings, doors, openings, room sizes and shapes), TERRAIN (ground relief, craters, rocks, outside), OBJECT-LOOK (a model unlike the concept: wrong make, scale or pick), OBJECT-MISSING (in the concept, absent in the scene, or read but not laid), ARRANGEMENT (where things stand: spacing, facing, height, floating, piling, joins), SURFACES (finishes, colours, materials, glass), LIGHT (level, colour, sky, lamps), CAMERA (the first view: framing, height, blocked lens), OTHER (say what)'

const RULES = `
House rules for this round (root CLAUDE.md applies in full; these are the ones that bite):
- Free only: no cloud runs, no Buy, no paid model calls, no accepts, rejects, waivers or locks. Readings and plan writings run under the owner's standing allowance only when the coordinator starts them, never from here.
- Never land an edit that moves the keys of paid model-making rows (picture-made models, people-dress, model bakes): the pre-push moved check lists what a commit moves; if model-making rows are on it, find another way or leave it undone and say so. Moving settle, light, film, sim-body and scene-record rows is fine with a Moved-rows trailer naming the environment's rework issue.
- Everything a place shows comes from the library: new shapes, kits and finishes are code-made library entries or data/library recipes, never a one-off.
- Checks are never loosened to pass. Fix the source a failure comes from.
- One test file per module with ONE test function; run only your module's test (make tests TESTS=<file>, under 60 s); write each break in its docstring and see it go red once.
- Heavy processes one at a time under systemd-run --user --scope -p MemoryMax=8G, only when free -g shows more than 12 GB available. Scratch goes under ${input.out}/<your label>.
- Land on main: scoped imperative commit ending "Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>", git fetch && git rebase origin/main, push with PROPS_HOME=$HOME/.score-this-pc git push origin HEAD:main; on a ref race rebase and retry, keeping the others' changes.
- Start no sub-agents, run no waiting loops, stop after about 2 hours of work.`

phase('Compare')
const groups = []
for (let i = 0; i < input.places.length; i += 4) groups.push(input.places.slice(i, i + 4))
const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    places: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          place: { type: 'string' },
          score: { type: 'number', description: '0-10, how close the still reads to the concept' },
          verdict: { type: 'string' },
          findings: { type: 'array', items: { type: 'string', description: 'CAUSE | breaks/noticeable/minor | what differs | evidence (file, value)' } },
        },
        required: ['place', 'score', 'verdict', 'findings'],
      },
    },
  },
  required: ['places'],
}
const compared = await parallel(groups.map((group, index) => () => agent(`
Read-only comparison for the ${input.environment} improve loop, round ${input.round}. Change nothing.
For each of your places (${group.join(', ')}): Read its locked concept picture and its still (${input.stills}/out/<place>.jpg; ${input.stills}/prep.jsonl says which stage each still shows) and look at both yourself. Score 0-10 how close the still reads to the concept, using the same scale every round: 0 nothing alike, 5 the room and its main objects read as the concept's, 8 a viewer would take it for the concept rendered, 10 indistinguishable in layout and look.
List every visible mismatch, one cause each from: ${CAUSES}. Trace each to the record or rule that made it (the PC store under $HOME/.score-this-pc/store: inventory reading, plan, scene record, assembly, gaps; code under score/stages, tools), with evidence. Factual only.
${input.notes || ''}`, { label: `compare-${index + 1}`, phase: 'Compare', schema: SCORE_SCHEMA, model: MODEL })))
const places = compared.filter(Boolean).flatMap(result => result.places)
const mean = places.reduce((sum, row) => sum + row.score, 0) / Math.max(1, places.length)
log(`round ${input.round}: ${places.length} places scored, mean ${mean.toFixed(1)}`)

phase('Causes')
const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    streams: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          key: { type: 'string' },
          cause: { type: 'string' },
          places: { type: 'array', items: { type: 'string' } },
          brief: { type: 'string', description: 'what to change, where in the code, what wave/round already did, what not to touch' },
        },
        required: ['key', 'cause', 'places', 'brief'],
      },
    },
    owner: { type: 'array', items: { type: 'string', description: 'a decision only the owner can make (money, a concept against a game number), with its price if known' } },
  },
  required: ['summary', 'streams', 'owner'],
}
const plan = await agent(`
You get round ${input.round}'s per-place findings for ${input.environment} (below). Read-only. Group them by root cause in the pipeline (a stage, a rule or a missing capability), rank by places hit times how badly, and make one fix stream per cause you find, however many that is. Two causes whose fixes would edit the same functions become one stream, so the streams can land side by side. Read the environment's rework issue first (gh issue view ${input.issue} --comments): never re-plan what earlier rounds landed; build on what they left undone. Each stream's brief names the code to change, the places it should move, and the neighbouring streams' code it must leave alone. Anything that needs money or the owner's judgement goes to "owner", not to a stream. Write the full ranked result to ${input.out}/round-${input.round}-causes.md.

${JSON.stringify(places)}`, { label: 'causes', phase: 'Causes', schema: PLAN_SCHEMA, model: MODEL })

phase('Fix')
const fixed = await parallel(plan.streams.map(stream => () => agent(`
You fix one cause of the ${input.environment} scenes being far from their locked concepts (improve loop round ${input.round}; issue #${input.issue}, read it with its comments first). The owner's goal: make the environment better, following the framework's rules and objectives.
Your cause: ${stream.cause}
Places: ${stream.places.join(', ')}
Brief: ${stream.brief}
Evidence: ${input.out}/round-${input.round}-causes.md; stills ${input.stills}/out/<place>.jpg.
${RULES}
Return: commits landed (hash, one line each), what changes in which places, what is left undone, and each decision you made (one line each, for the owner's review).`,
  { label: stream.key, phase: 'Fix', isolation: 'worktree', model: MODEL })
  .then(report => ({ key: stream.key, report }))))

return { round: input.round, mean, places, summary: plan.summary, owner: plan.owner, streams: plan.streams, fixed: fixed.filter(Boolean) }
