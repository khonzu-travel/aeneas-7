# Platform — Turn Queue and Workers

The turn queue is how the platform gives work to roles. It replaces v6's
notification dispatch, outbox, per-agent webhooks, reconciliation sweeps, and
claim projection with one table and one protocol.

---

## A turn

| Field | Meaning |
|---|---|
| `turn_id` | UUID |
| `kind` | What the turn is: `spec.author`, `spec.clarify-apply`, `plan.author`, `plan.revise`, `plan.analyze`, `review.architecture`, `review.data`, `review.security`, `review.ux`, `task.test`, `task.implement`, `task.fix`, `task.triage`, `defect.resolve`, `integrate`, `release`, `constitution.author`, `amend.author`, `observe`, `triage-anomaly` |
| `role` | The role the turn runs as; determines the permission set and the skills allowed |
| `skill`, `skill_version` | The skill the worker must load |
| `stream_type`, `stream_id`, `feature_id` | The scope the token is minted for |
| `trigger` | The event (`commit_xid`) that called for the turn |
| `inputs` | Artifact references and reports the skill starts from: versions, verifier report ids, review verdicts, the analyze report |
| `priority`, `not_before`, `deadline` | Ordering, backoff, and the point at which an unclaimed turn is an alert |
| `attempt`, `max_attempts` | Bound on retries |
| `budget` | Token and cost ceiling from the skill, adjustable per project |
| `status` | `QUEUED` · `CLAIMED` · `DONE` · `FAILED` · `CANCELLED` |
| `worker_id`, `lease_expires_at`, `last_heartbeat_at` | Liveness |
| `usage`, `result` | Reported by the worker; `result` is structured per kind |

Turns are rows in `turns`; they are not events. The event that called for a
turn is on its stream; the turn's completion signals write further events
there. The queue itself is operational state, rebuildable from the streams if
lost (every enqueue rule is a function of an event).

---

## Enqueue rules

The Custodian enqueues turns in the same transaction as the event that calls
for them. The rule set is a table, not code paths:

| Event | Turn(s) enqueued |
|---|---|
| `FeatureCreated` | `spec.author` (analyst) |
| `ClarificationAnswered` | `spec.clarify-apply` or `plan.clarify-apply` for the asker |
| `SpecRejected` | `spec.author` with the reasons |
| `SpecApproved` | `plan.author` (planner) |
| `PlanSubmitted` (deterministic passes green) | `plan.analyze` (analyzer) |
| `PlanAnalyzed` (no `CRITICAL`) | one `review.*` per required reviewer, in parallel |
| `PlanAnalyzed` (`CRITICAL`) or `PlanRejected` | `plan.revise` with the report, verdicts, and patches |
| `PlanApproved` | none (the scheduler acts) |
| `TaskReady` | `task.test` or `task.implement` for the task's role |
| `VerifierRunFailed` (attempts remain) | `task.implement`/`task.test` again with the report |
| `VerifierRunFailed` (acceptance or contract test, later task or integration) | `task.triage` (tester) |
| `BugRaised` / `DefectRaised` | `task.fix` / `defect.resolve` |
| `IntegrationStarted` | `integrate` |
| `IntegrationSucceeded` | `release` |
| `AmendmentApplied` | `plan.analyze` for every affected open Plan |
| `AnomalyRulesFired` | `observe` |

**One live turn per `(feature_id, kind, artifact)`.** A partial unique index
on `turns (feature_id, kind, artifact_ref) WHERE status IN ('QUEUED','CLAIMED')`
makes a second enqueue of the same work a no-op. This is the structural form
of the v6 "two turns opening the same Story" fix: the queue cannot hold two
authoring turns for one artifact.

**Supersession cancels.** A new artifact version cancels queued review and
analyze turns for the previous version; a claimed one keeps running but its
completion is refused with `SUPERSEDED` and recorded as such. Abandonment
cancels every queued turn on the feature.

---

## Claiming

```sql
WITH next AS (
  SELECT turn_id FROM turns
  WHERE status = 'QUEUED'
    AND role = ANY($roles)
    AND not_before <= now()
    AND NOT EXISTS (SELECT 1 FROM skill_standdowns s
                    WHERE s.skill = turns.skill AND s.cleared_at IS NULL)
  ORDER BY priority ASC, created_at ASC
  FOR UPDATE SKIP LOCKED
  LIMIT 1)
UPDATE turns t SET status = 'CLAIMED', worker_id = $worker,
       lease_expires_at = now() + $lease, last_heartbeat_at = now(),
       attempt = attempt + 1
FROM next WHERE t.turn_id = next.turn_id
RETURNING t.*;
```

The response carries the turn and a **turn token**: a signed claim of
`{turn_id, role, feature_id, stream_id, artifact_scope, exp}` with `exp` at
the lease end. Heartbeats extend the lease and reissue the token. The
Custodian honors a token only while the turn is `[CLAIMED]`, so a revoked or
lapsed turn's token fails on its next write.

`priority` is computed at enqueue: feature priority, then phase weight
(integration and fixes ahead of new authoring, so work in flight finishes
before new work starts), then age. A per-role queue cap and `MAX_BUILD_WIP`
bound what enters the queue at all.

---

## Completing and failing

`complete` carries the structured `result` for the kind (for example a review
turn's verdict id, an implement turn's branch commit) and `usage`. The
Custodian records `TurnCompleted` on the turn's stream and marks the row
`DONE`. A turn that made no write and reports no result is refused: a turn
must end in a signal or a failure.

`fail` carries `reason`, `retryable`, and `usage`. Retryable failures requeue
with exponential `not_before` while attempts remain; then `FAILED`. A failure
classified as **configuration** — the model endpoint refused the credentials
(401/402/403) or the model id (404), or the skill version is missing — writes
a `skill_standdowns` row: no turn for that skill is claimable until an Admin
clears it, and the queue shows every turn it is holding. One bad model id
stands down one skill; every other role keeps working. A content refusal by
the model is non-retryable for that turn and surfaces on the artifact as
`waiting_on: delivery_lead` with the reason.

Budget exhaustion fails the turn with `BUDGET` and is retryable once at the
next model tier if the skill allows it.

---

## Leases and the reaper

A claimed turn whose lease lapses is requeued by the reaper (attempt count
kept). The worker that held it, if alive, finds its token refused and stops.
Because every skill derives its work from the artifact rather than from
anything held in memory, re-running a turn is safe; because every write is
idempotent by key, a retried write cannot duplicate.

---

## Worker protocol

```
loop:
  turn ← POST /v1/turns/claim { roles: [...], worker_id }
  if none: sleep(backoff); continue
  materialize working tree if skill.needs_fs
  load skill(turn.skill, turn.skill_version)
  run skill with turn.inputs, calling /v1 with the turn token,
      heartbeating every N seconds with usage so far
  POST /v1/turns/{id}/complete { result, usage }
    or POST /v1/turns/{id}/fail { reason, retryable, usage }
```

A worker registers with the Admin surface (id, roles, skills, model tiers)
so that the queue can report a turn no registered worker can serve — a
`QUEUED` turn past `deadline` with no capable worker is an operator alert,
not a silent stall.

---

## Observability

Per role and per kind: queue depth, oldest queued age, claim latency, turn
duration, attempts per completed turn, failure classes, usage and cost. These
feed the `turn_metrics` projection and are non-governing, except that a turn
past `deadline` and a skill stand-down are surfaced as conditions on the
features they hold.
