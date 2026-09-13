# Platform — Overview

The platform owns all state, runs all loops, and is the sole writer to every
data store. Workers and humans signal; the platform validates, writes,
records, verifies, schedules, and integrates.

---

## Components

| Component | Runs | Owns |
|---|---|---|
| **Custodian** | in the API process, per request | Validation, the one transaction per write, event append, entity update, turn enqueue |
| **Turn queue** | a table | The work owed to roles; claims, leases, tokens |
| **Projectors** | background, one per read model | Queues, boards, dashboards, inboxes, metrics; a checkpoint each |
| **Verifier runner** | background, sandboxed | Verifier suites, analyze deterministic passes, risk scores |
| **Scheduler** | background, event-driven | Releasing approved Plans into Build under priority, predecessors, blockers, WIP, and write-set rules |
| **Merge queue** | background, one repo at a time | Integrating finished features onto the trunk |
| **Reaper** | background, periodic | Requeuing lapsed turns, re-driving interrupted verifier runs |
| **Renderer** | on demand | Artifact versions as Markdown and as files in a feature's working tree |
| **UI** | web | Human intent capture, decisions, answers, inboxes, dashboards, audit |

Everything except the Custodian is an asynchronous consumer of the event
store or the turn queue. Nothing asynchronous participates in a governing
decision: gates read entity state inside the Custodian's transaction.

---

## Architecture

```
  Workers ───── /v1 (turn token) ────┐          ┌──── /v1 (session) ───── UI ── Humans
                                     ▼          ▼
                          ┌──────────────────────────────┐
                          │          CUSTODIAN           │
                          │ authenticate → validate →    │
                          │ one transaction per stream:  │
                          │  content version · entity    │
                          │  state · event · turns ·     │
                          │  reservations · counters     │
                          └──────────────┬───────────────┘
                                         │ commit (commit_xid)
             ┌───────────────┬───────────┴──────────┬────────────────┬──────────────┐
             ▼               ▼                      ▼                ▼              ▼
        Projectors     Verifier runner         Scheduler        Merge queue      Reaper
        (checkpoint)   (sandbox, reports)    (gate → release)  (rebase, verify,  (leases,
                                                                 merge, deploy)   re-drives)
             │               │                      │                │              │
             └───────────────┴──────── signals back through the Custodian ─────────┘
```

Background components never write to the database directly. They call the
Custodian with a platform identity, so their writes are validated and audited
like any other.

---

## The Custodian sequence

For every write:

1. **Authenticate**: a turn token (worker) or a session (human). A turn token
   is honored only while its turn is `[CLAIMED]` and its lease is live.
2. **Authorize**: the role's permission set against the artifact type, the
   artifact's stream against the token's scope, and the artifact's current
   status against the signal.
3. **Validate**: format conformance, gate conditions, bounds, reservations.
   A refusal returns the reason and writes nothing.
4. **Begin** a transaction; read the stream head.
5. **Write** the content version (if any), the entity state, the event at
   `head + 1`, the turns the event calls for, reservations and counters.
6. **Commit**. A unique-index conflict on `(stream_id, stream_seq)` means a
   concurrent write landed on this stream; retry from step 2 up to three
   times, then refuse with `CONFLICT`.
7. **Return** the result and the commit position (`commit_xid`), which a
   caller may pass to a read that needs to observe it.

No locks are taken beyond the row-level ones the unique index implies. Two
writes to different streams never interact. See [`event-store.md`](event-store.md).

---

## API surface (sketch)

| Area | Endpoints | Caller |
|---|---|---|
| Turns | `POST /v1/turns/claim` · `POST /v1/turns/{id}/heartbeat` · `POST /v1/turns/{id}/complete` · `POST /v1/turns/{id}/fail` | workers |
| Feature Spec | `POST /v1/features/{f}/spec/versions` · `POST /v1/features/{f}/spec/submit` · `GET /v1/features/{f}/spec[@version]` | analyst turn |
| Plan | `POST /v1/features/{f}/plan/versions` (the bundle) · `POST /v1/features/{f}/plan/submit` · `GET …` | planner turn |
| Reviews | `POST /v1/features/{f}/plan/reviews` (verdict) | reviewer turns |
| Tasks | `GET /v1/features/{f}/tasks` · `POST /v1/tasks/{t}/implementation-complete` | implementer / tester turns |
| Clarifications | `POST /v1/clarifications` · `POST /v1/clarifications/{c}/answers` · `POST /v1/clarifications/{c}/apply` | roles, humans |
| Blockers | `POST /v1/blockers` · `POST /v1/blockers/{b}/clear` | roles, Delivery Lead |
| Decisions | `POST /v1/decisions` (approve / reject / abandon / schedule override / risk acceptance) | humans |
| Constitution | `POST /v1/constitution/versions` · `POST /v1/amendments` · … | architect turn, humans |
| Data Model | `GET /v1/data-model` · `POST /v1/data-model/changes` (independent) | all / data reviewer |
| Reads | `GET /v1/features/{f}` (aggregate with derived phase, `waiting_on`, `blocked`) · projections under `/v1/views/*` with `?after=` cursors and optional `?min_commit=` | all |
| Admin | worker registry, skill versions, model tiers, stand-downs, projection rebuild, turn retry | Admin, Delivery Lead |

Every write accepts an `Idempotency-Key`; a retried key replays the original
result. Every response carries `commit_xid`.

---

## Human UI

The UI is a projection consumer plus a decision submitter. It shows each
human role an **inbox** of decisions and answers owed, the feature dashboard
with derived phase and `waiting_on`, the board, blockers, budgets, and the
audit trail; and it submits decisions, clarification answers, intent, and
abandonment through the Custodian. Humans never see the turn queue except as
"waiting on planner" on a feature, and never see a worker.

---

## Detailed documents

- [`turn-queue.md`](turn-queue.md) — turns, workers, tokens, leases
- [`event-store.md`](event-store.md) — streams, optimistic concurrency, partitioning, taxonomy
- [`projections.md`](projections.md) — projectors, checkpoints, read-your-writes, rebuild
- [`concurrency.md`](concurrency.md) — isolation by stream, write sets, branches, merge queue
- [`verification.md`](verification.md) — verifier suites, analyze gate, risk score
- [`database-schema.md`](database-schema.md) — tables
- [`recovery.md`](recovery.md) — what survives a crash and how
