# Overview

AENEAS 7 is a governed delivery platform built as a set of declared loops. This
document is the whole system in one place; every section links to the document
that owns the detail.

---

## The shape

```
 Humans (UI)                                  Workers (pool, stateless)
   │ intent, approvals, answers                 │ claim turn → load skill → act → complete
   ▼                                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                               PLATFORM                                    │
│                                                                           │
│  Custodian ── validates every signal, writes content + event + turns      │
│              in one transaction per stream                                │
│                                                                           │
│  Streams ── one event stream per Feature / Constitution / Data Model      │
│  Turn queue ── the work owed to roles; claimed with leases                │
│  Verifiers ── sandboxed tests, contracts, scans, analyze gate, risk score │
│  Scheduler ── priority, predecessors, blockers, WIP, write-set conflicts  │
│  Merge queue ── one integration at a time onto the trunk                  │
│  Projectors ── async, checkpointed read models for queues and dashboards  │
│                                                                           │
│  PostgreSQL: entity tables (aggregate state) · events · turns · content   │
└───────────────────────────────────────────────────────────────────────────┘
```

The platform is the sole writer. Workers and humans signal; the platform
validates, writes, and records. No one else evaluates a gate or writes a
status.

---

## Artifacts

| Artifact | File form | Answers | Authored by role | Approved by |
|---|---|---|---|---|
| Charter | `charter.md` | What is this project, who is it for, what must it never do | analyst (interview with the Product Owner) | Product Owner |
| Constitution | `constitution.md` | The non-negotiable principles and the vocabulary every Plan must conform to | architect | Solution Architect, Enterprise Architect |
| Feature Spec | `spec.md` | What, for whom, why; how we will know it is done | analyst | Product Owner |
| Plan | `plan.md` + `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `threat-model.md`, `checklists/` | How, within the Constitution | planner | reviewers (architecture, data, security, UX), then Solution Architect |
| Tasks | `tasks.md` | The ordered, parallelizable units of build work | planner | with the Plan |
| Data Model | one document per entity / enumeration / overview | The project's logical data design as approved and built | platform transcribes from approved Plans | with the Plan; independent changes have their own review |
| Clarification | a session log inside the artifact it clarifies | The questions asked and the answers that resolved them | analyst / planner / reviewer | the human or role that answered |
| Amendment | `amendments/A-####.md` | A governed change to the Constitution | architect | Solution Architect, Enterprise Architect |

Every artifact is versioned append-only in the content store and rendered
into the feature's working tree under `specs/F-####-slug/` so that skills and
coding tools read it as files. See [`ledger/`](ledger/).

---

## Loops

A loop is a generator turn, a verifier, a bound, and a stop. The six phases are
six loops, and the whole feature is one outer loop bounded by its budget.

| Phase | Generator (role · skill) | Verifier | Bound | Stop / escalation |
|---|---|---|---|---|
| 1 Specify | analyst · `specify`, `clarify` | Spec format check; no unresolved `[NEEDS CLARIFICATION]`; Product Owner approval | `MAX_CLARIFY_SESSIONS`, `MAX_SPEC_REJECTIONS` | Product Owner decides: revise intent or abandon |
| 2 Plan | planner · `plan`, `tasks` | Analyze gate; Constitution check; data-model gates; parallel review round; Solution Architect approval | `MAX_PLAN_REJECTIONS`, `MAX_REVIEW_QUESTIONS` per reviewer per version | Solution Architect decides: redirect, amend the Constitution, or abandon |
| 3 Schedule | platform scheduler | Gate conditions (approved, predecessors done, unblocked, WIP, write set) | none (deterministic) | Delivery Lead may reorder or force |
| 4 Build | tester · `test`; implementer · `implement` | Sandboxed verifier suite per task; frozen acceptance tests | `MAX_VERIFY_ATTEMPTS` per task, `MAX_BUG_RECURRENCE` per feature | Recurring failure becomes a Defect to the planner; then a Solution Architect review |
| 5 Integrate & Release | integrator · `integrate`, `release` | Rebase onto trunk, full verifier suite, risk band, deploy health | `MAX_INTEGRATION_ATTEMPTS` | Conflict or red trunk raises a blocker to the Delivery Lead; `HIGH` band waits for the Solution Architect |
| 6 Operate | operator · `observe`, `triage` | Anomaly rules | none | An anomaly becomes a new Feature; no self-remediation |

See [`pipeline/`](pipeline/). Bounds are counted by the platform and refused
at the signal; see [`governance.md`](governance.md).

---

## Turns and workers

A **turn** is the unit of work the platform owes a role. It names the role,
the skill, the feature, the triggering event, the artifact scope, a budget,
and a deadline. Turns are enqueued by the Custodian in the same transaction
as the event that calls for them. A **worker** claims a turn it can run, is
issued a token good only for that turn, loads the skill, does the work through
the `/v1` API, and completes or fails the turn. There are no per-role
processes and no notifications to agents.

Five properties of a turn are what make work survive load, and each one is a
failure v6 could not prevent because it had no unit of work to attach them to:

| Property | Consequence |
|---|---|
| At most **one live turn** per `(stream, kind, artifact)` | Two workers never author one artifact |
| Exactly **one committing write** per turn | A turn cannot leave an artifact half-created |
| **Checkpoints** stored as it goes | A requeued turn resumes instead of re-deriving |
| A **heartbeat that answers** `CURRENT` / `SUPERSEDED` / `CANCELLED` | A stale turn stops before its next model call |
| A **lease sized from the skill**, heartbeated on a reserved connection | A lapsed lease means a dead worker, not a busy platform |

See [`platform/turn-queue.md`](platform/turn-queue.md) and
[`roles.md`](roles.md).

---

## Streams and projections

Every event belongs to a stream — a Feature, the Constitution, the Data Model,
or the platform — and streams are written with optimistic concurrency, so
parallel features never wait on each other. Gates read aggregate state on the
entity tables, in the same transaction. Projections are asynchronous read
models rebuilt from a checkpoint. See
[`platform/event-store.md`](platform/event-store.md) and
[`platform/projections.md`](platform/projections.md).

---

## Where parallel features meet

There are exactly three shared resources across features, and each has one
structural rule:

| Shared resource | Rule |
|---|---|
| The Data Model lexicon | A name is reserved by the first Plan to declare it at submit; a second is refused. `BREAKING` changes are refused at the gate and go through the Data Model's own review |
| The Constitution | Amended rarely; an applied Amendment enqueues a re-analyze turn for every Plan not yet integrated |
| The codebase | Every Plan declares its write set; the scheduler holds overlapping features; every feature builds on its own branch; the integrator merges one feature at a time onto the trunk |

See [`platform/concurrency.md`](platform/concurrency.md).

---

## Verification and risk

A worker's completion signal starts verification; it never ends it. The
platform runs the verifier suite for the task — build, lint, type-check, unit
tests, frozen acceptance tests, contract tests, scanners, checklist assertions
— in a sandbox against the feature branch. Failure returns the task; success
completes it. At integration the platform computes a risk score from
deterministic signals and maps it to a band; `MEDIUM` and `HIGH` wait for a
Solution Architect. See [`platform/verification.md`](platform/verification.md).

---

## Governance in one paragraph

Rules are structural or they are not rules. The platform: is the only writer;
issues every identifier; owns every status; counts every bound; runs every
verifier; enforces every role permission on a per-turn token; keeps the event
store and content versions append-only; and refuses, with a reason, anything
that does not fit. The list is in [`governance.md`](governance.md).
