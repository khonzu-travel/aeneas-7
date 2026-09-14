# Platform — Projections

A projection is a read model built asynchronously from the event store by a
**projector** with a durable **checkpoint**. Projections serve queues,
inboxes, boards, and dashboards. They never sit in the write path and are
never consulted for a governing decision.

---

## Why asynchronous

v6 updated every projection inside the Custodian's transaction. Every write
paid the cost of every read model it touched, the ready board rewrote a
feature's rows on each task event, and a slow projection update lengthened
the lock every other writer on that artifact waited for. Under parallel
features the write path was the sum of its read models.

In v7 the write path is the stream and the entity row. Read models catch up
behind a checkpoint, in batches, on their own schedule. A gate that needs the
current state reads the entity row in the same transaction; nothing that
decides anything reads a projection.

---

## Projector contract

```
loop:
  batch ← events WHERE commit_xid > checkpoint AND commit_xid < watermark ORDER BY commit_xid LIMIT N
  BEGIN
    for e in batch: apply(e)          -- idempotent per event
    checkpoint ← max(batch.commit_xid)
  COMMIT
  if batch was full: continue immediately
  else: wait for NOTIFY 'events' or poll interval
```

- One row per projector in `projection_checkpoints (name, commit_xid, updated_at)`.
- Handlers are idempotent per event so a crash between apply and checkpoint
  is harmless.
- With replicas, each projector takes `pg_try_advisory_lock(hash(name))`; the
  others stand by. This is the only advisory lock in the system besides the
  merge queue's.
- A projector that throws on an event records the event and the error in
  `projection_errors`, skips it, and continues; the operator sees a lagging,
  erroring projector rather than a stalled system.

**Read-your-writes.** Every write returns its `commit_xid`. A read of a
projection may pass `?min_commit=<xid>`; the API waits (bounded, default
2 s) for the projector's checkpoint to pass it, then serves the page, or
serves it flagged `stale: true` if the bound expires. UI decision flows use
this so a human sees their own decision reflected immediately.

**Rebuild.** Truncate the projection, reset its checkpoint to zero, let it run.
`ProjectionRebuilt` is recorded on the platform stream.

---

## Read models

| Projection | Serves | Keyed by | Ordering |
|---|---|---|---|
| `human_inbox` | Each human role's owed decisions and answers: spec approvals, plan approvals, risk acceptances, clarification sessions, held features, budget holds | `(human_role, item)` | urgency (bound reached, then age) |
| `backlog` | `[APPROVED]` Plans not yet scheduled with the scheduler's current hold reason | `feature_id` | priority, then key |
| `board` | Every task of every feature in Build with status, role, attempt, blocked flag, the turn holding it | `task_id` | feature priority, then task key |
| `feature_dashboard` | One row per feature: derived phase, `waiting_on`, `blocked`, budget spent/remaining, bounds consumed, last event | `feature_id` | last event desc |
| `blockers` | Open blockers with the artifact, raiser, reason, resume context, and the human that owns clearing them | `blocker_id` | age |
| `review_status` | Open review stages: reviewer, decision, verdict id | `(feature_id, reviewer)` | — |
| `merge_queue_view` | Features `[INTEGRATING]`: position, attempts, risk band, waiting on whom | `feature_id` | position |
| `pen_holder` | Every artifact with a live turn against it: the turn, kind, skill version, worker, heartbeat age, checkpoints stored, budget spent | `artifact_ref` | heartbeat age desc |
| `turn_metrics` | Queue depth, claim latency, duration, attempts, checkpoints, failure classes per role and kind; stand-downs | `(role, kind, window)` | — |
| `intake_queue_view` | Intent queued behind `MAX_OPEN_FEATURES`, with position | `id` | position |
| `budget_ledger` | Usage and cost per feature, per turn kind, per model tier, against budget | `feature_id` | — |
| `data_model_impact` | For each document, live citing features; reservations by feature | `document_id` | — |
| `audit_feature` | Rendered timeline per feature | `feature_id` | `stream_seq` |

The turn queue is a table, not a projection: it is written by the Custodian
and read by workers directly.

`pen_holder` is the answer to "why has this artifact not moved". A live turn
with a recent heartbeat is work in progress; one with a stale heartbeat is a
worker that died and a lease about to lapse; no turn at all on an artifact
that is not terminal and not waiting on a human is a missing enqueue, which is
an alert. In v6 these three were indistinguishable — an agent working, an
agent crashed, and an agent that never got the notification all looked like an
artifact sitting still.

---

## Paging

Every projection read is one bounded page with keyset paging: the ordering
ends in a unique column, the page returns an opaque cursor, and a cursor from
another queue is refused. Offsets are not used.

---

## Derived phase

A feature's phase is computed by the projector from the Plan and Spec
statuses and the tasks, never stored on the entity and never computed by a
client:

| Phase | Condition |
|---|---|
| Specify | Spec not `[APPROVED]` |
| Plan | Spec `[APPROVED]`, Plan not `[APPROVED]` |
| Scheduled | Plan `[APPROVED]` and not `[SCHEDULED]` |
| Build | Plan `[SCHEDULED]` or `[IN_BUILD]` |
| Integrate | Plan `[INTEGRATING]` |
| Release | integration succeeded, no `DeploymentCompleted` |
| Done / Abandoned | terminal |
