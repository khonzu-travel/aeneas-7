# AENEAS 7 — Design

**AI-Enhanced Nimble Engineering & Automation System**, seventh design.

AENEAS is a governed software delivery platform: it turns human intent into
integrated, verified, deployed software through a pipeline of **loops** run by
a **pool of workers** executing **role skills**, under a **platform** that owns
every state transition and records every decision.

This repository is the design specification only. It supersedes the design in
`aeneas-6`. The implementation is a separate concern and follows this design;
the design is the authority.

> AENEAS 7 is a loop engine. A human states what they want and approves what the
> system understood. The platform then runs bounded generate → verify → retry
> loops — specify, plan, build, integrate — each with a declared verifier, a
> declared bound, and a declared stop. Workers are interchangeable; roles are
> permission sets; artifacts have fixed formats; every action traces to an
> event, every event to an artifact, every artifact to a human approval.

## What changed since AENEAS 6

| Concern in v6 | v7 answer | Where |
|---|---|---|
| Spec authoring took many serialized agent turns (Commissions to specialists, incorporation, settlement) | One **planner** turn produces the whole Plan bundle with Spec Kit-shaped skills; specialists **review in parallel**, once, with structured checklists. Commissions are gone | [`design/changes-from-v6.md`](design/changes-from-v6.md) §1, [`design/pipeline/phase-2-plan.md`](design/pipeline/phase-2-plan.md) |
| Twelve long-lived agents, each a single process with its own sweeps; the roster failed under load | A **worker pool** pulls **turns** from a platform-owned queue. A role is a skill bundle plus a permission set minted into a per-turn token, not a process. Scale by adding workers | [`design/changes-from-v6.md`](design/changes-from-v6.md) §2, [`design/platform/turn-queue.md`](design/platform/turn-queue.md), [`design/roles.md`](design/roles.md) |
| Story and Spec were free-form prose | Artifacts adopt **Spec Kit** formats: the Feature Spec is `spec.md` (prioritized user stories, FR-###, SC-###, `[NEEDS CLARIFICATION]`), the Plan is the `plan.md` bundle (research, data-model, contracts, quickstart, threat-model), Tasks are `tasks.md` (T###, `[P]`, `[US#]`). The Constitution replaces the Archetype | [`design/changes-from-v6.md`](design/changes-from-v6.md) §3, [`design/ledger/`](design/ledger/) |
| One global event table, per-artifact advisory locks, projections updated inside the write transaction — contention and a growing write cost as features ran in parallel | **Per-feature event streams** with optimistic concurrency, **asynchronous checkpointed projections** that never sit in the write path, gates that read aggregate state rather than projections, and **write-set-aware scheduling** plus a **merge queue** so parallel features stop colliding in the codebase | [`design/changes-from-v6.md`](design/changes-from-v6.md) §4, [`design/platform/event-store.md`](design/platform/event-store.md), [`design/platform/concurrency.md`](design/platform/concurrency.md) |
| Other | Platform-run verifiers replace agent-scored `changeDelta`; deterministic scheduling replaces the Scrum Master agent; an `analyze` gate returns broken plans before any reviewer spends a turn; the Data Model is transcribed by the platform at integration; blocked is a condition rather than a status; per-feature budgets are a governed bound; per-skill model routing | [`design/changes-from-v6.md`](design/changes-from-v6.md) §5 |

## Reading order

1. [`design/overview.md`](design/overview.md) — the shape of the system in one document
2. [`design/changes-from-v6.md`](design/changes-from-v6.md) — every decision, with the v6 concept it replaces and why
3. [`design/roles.md`](design/roles.md), [`design/governance.md`](design/governance.md) — who may do what, and what the platform refuses
4. [`design/ledger/`](design/ledger/) — the artifact formats
5. [`design/pipeline/`](design/pipeline/) — the six phases as loops
6. [`design/platform/`](design/platform/) — the machinery: turns, streams, projections, concurrency, verification
7. [`design/workflows/`](design/workflows/) — end-to-end and alternate flows
8. [`design/skills/`](design/skills/) — the skill catalog and an exemplar
9. [`roadmap.md`](roadmap.md) — the build epics

## Repository layout

| Directory | What it is |
|---|---|
| `design/` | The canonical design specification (Markdown only). The source of truth for what the system does |
| `design/skills/` | The role skill catalog: what each skill takes, produces, may call, and is verified by |
| `roadmap.md` | The build backlog at epic granularity. Stories are derived from it when implementation begins |

## Vocabulary

| Term | Meaning |
|---|---|
| **Feature** | The unit of delivery. One Feature Spec, one Plan, one task list, one branch, one event stream |
| **Turn** | One unit of worker execution: a role, a skill, a trigger, an artifact scope, a budget, a result. The platform queues turns; workers claim them |
| **Role** | A permission set and a skill bundle. A turn runs *as* a role. Roles are not processes |
| **Skill** | A versioned instruction-and-tool bundle a worker loads to execute a turn of a given kind |
| **Loop** | A generator turn, a verifier, a bound, and a stop condition, declared together |
| **Verifier** | A deterministic check the platform runs on a deliverable. A worker's claim of success is never sufficient |
| **Stream** | The ordered event history of one aggregate (a Feature, the Constitution, the Data Model). Streams never contend with one another |
