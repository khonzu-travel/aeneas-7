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
| `expected_seconds`, `slots` | Declared by the skill: how long a turn of this kind normally takes, and how much of a worker it occupies. The platform sizes the lease from the first and admission from the second |
| `checkpoint_seq` | The last checkpoint the turn stored; a requeued attempt starts from it |
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

## One committing write per turn

**A turn performs any number of reads and exactly one committing write.** The
platform refuses a second committing write on the same turn token, naming the
write that already landed.

This is the rule v6 most needed and did not have. A v6 spec-authoring turn
called create, then draft, then one task-create per task, then one commission
request per specialist, then submit — a dozen mutations with no transaction
around them, so any failure in the middle left a spec with no version, half a
task graph, or a commission the settlement gate would then wait on forever.
Every repair for that was a resume path for one more partial state.

The rule is affordable because every artifact in v7 is submitted whole:

| Turn kind | Its one write |
|---|---|
| `spec.author` | the `spec.md` version (submit-for-review is part of the same signal when the format gates pass) |
| `plan.author`, `plan.revise` | the whole bundle, `tasks.md` included, as one version |
| `review.*` | the verdict |
| `plan.analyze` | the analyze report |
| `task.test`, `task.implement`, `task.fix` | implementation-complete naming the branch commit |
| `task.triage` | the Bug or Defect raise |
| `spec.clarify`, `review.*` asking | the clarification session |
| `*.clarify-apply` | the revised version plus the session's application, one signal |
| `integrate` | the rebased head |
| `release` | the deployment outcome |
| `amend.author` | the Amendment version |

Work a skill does on the filesystem — commits on a feature branch — is not a
committing write: the branch is scratch space until the one signal names a
commit. A turn that finds it needs a second write has been mis-specified; it
ends and the platform enqueues the next turn.

So a turn ends in exactly two ways: its one committing write — which for some
kinds is an opened clarification session rather than a submission — or a
failure. Either way it is one atomic, idempotent call, and the artifact is
whole on both sides of it.

---

## Checkpoints

A planner turn can run for many minutes and spend a large fraction of a
feature's budget. Without checkpoints, a lease lapse or a worker crash
discards all of it and the requeued attempt pays for the same tokens again.
Wasted model output, not wasted wall-clock, was the expensive part of v6's
failures.

```
POST /v1/turns/{id}/checkpoint { label, payload, usage }
  → { checkpoint_seq }
```

A checkpoint is an intermediate result stored against the turn: a rendered
artifact file, a sub-skill's output, a resolved research decision, a diff not
yet committed. Checkpoints are **not** events and **not** content versions:
they carry no authority, nothing reads them for a decision, and they are
deleted when the turn reaches `DONE` or is cancelled. They exist only so that
attempt *n+1* starts where attempt *n* stopped.

- Writing a checkpoint extends the lease, so it doubles as a heartbeat.
- A requeued turn is handed `checkpoint_seq` and the stored payloads as
  additional `inputs`. The skill decides what to reuse; the platform requires
  nothing of it.
- Checkpoints are bounded per turn (count and total bytes, from the skill's
  declaration). Exceeding the bound fails the write, not the turn.
- A checkpoint is the only thing a turn writes that is not its one committing
  write, and it is exempt precisely because it changes no governed state.

Skills declare where their checkpoints fall. The `plan` skill checkpoints
after each sub-skill, so a crash in `tasks` does not re-derive `data-model.md`
and `contracts/`.

---

## Heartbeats say whether the turn is still current

The heartbeat response carries the turn's current standing:

```
POST /v1/turns/{id}/heartbeat { usage }
  → { status: "CURRENT" | "SUPERSEDED" | "CANCELLED",
      lease_expires_at, token, budget_remaining }
```

A worker that reads anything but `CURRENT` **stops before its next model
call**, reports `fail` with that reason, and takes the next turn. In v6 a turn
whose artifact had moved underneath it discovered this only when its final
write was refused, having already paid for every token it spent. Cancellation
at the heartbeat bounds that waste to one heartbeat interval.

`budget_remaining` lets a skill shorten its own work — drop an optional
section, skip a repair pass — rather than being failed at the ceiling mid-call.

Supersession is the same rule as before, moved earlier: a new artifact version
cancels queued review and analyze turns and marks claimed ones `SUPERSEDED`,
and abandonment cancels every turn on the feature.

---

## Leases are sized by the skill, not by a global constant

Each skill declares `expected_seconds`. The platform sets the lease to
`max(min_lease, lease_factor × expected_seconds)` (default factor 3) and the
heartbeat interval to a fraction of it.

A single global lease is wrong in both directions: long enough for a planner
turn, it leaves a crashed triage turn stuck for a quarter of an hour; short
enough for triage, it reaps planner turns that are working. v6 had one
constant, and the heartbeat that was supposed to cover the difference competed
for the same connection pool as every board read — so a lease lapse under load
meant "the platform is busy", not "the worker died", and the reaper reclaimed
live work.

Two rules keep that from recurring:

- **Heartbeats are cheap and independent.** The heartbeat path touches one
  indexed row, takes no lock beyond that row, and is served from a connection
  allowance reserved for it. It can never queue behind a projection read or a
  long report query.
- **A lapse is evidence, not proof.** Requeuing re-validates under the row
  lock, so a turn that heartbeats between detection and requeue is left alone.

---

## Admission: slots and intake

Two counters bound how much work can be in flight, so that overload is a queue
that grows rather than a system that thrashes:

| Counter | Bounds | Set by |
|---|---|---|
| `slots` per worker | Concurrent turns one worker runs; each skill declares its slot cost | worker registration + skill |
| `MAX_OPEN_FEATURES` | Features not yet `[DONE]` or `[ABANDONED]` | project |

`MAX_OPEN_FEATURES` is backpressure at intake. `MAX_BUILD_WIP` bounds Build,
but in v6 nothing bounded the phases before it, so a burst of intent produced
a burst of authoring and review turns competing for the same workers, models,
and reviewers. Intent submitted past the cap is queued as `PENDING_INTAKE`
with its position, visible to the Product Owner, and admitted as features
close.

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

`class` says what kind of failure it was, because the responses differ:

| Class | Example | Response |
|---|---|---|
| `TRANSIENT` | timeout, rate limit, 5xx | requeue with backoff, resume from checkpoint |
| `CONFIGURATION` | rejected key, unknown model id, missing skill version | stand down the skill; an Admin clears it |
| `SUPERSEDED` | the artifact moved under the turn | no retry; the replacement turn is already queued |
| `BUDGET` | turn or feature ceiling reached | one retry at the next tier, or a blocker to the Product Owner |
| `CONTENT` | the model refused the request | no retry; `waiting_on: delivery_lead` with the reason |
| `INPUT` | the turn's inputs do not resolve (a version was abandoned) | no retry; the platform re-derives whether a turn is still owed |

Two classes v6 had and v7 does not: a **format** failure and a **parse**
failure. Those are handled inside the turn — every model call is validated
against the schema the skill declares for that output, and a failure runs the
skill's bounded repair pass — so a truncated JSON object or a missing spec
section costs one small call instead of a requeued turn that will truncate
again. A repair pass that does not converge fails the turn as `TRANSIENT`
with the invalid output attached, and the next attempt starts from the last
good checkpoint.

---

## Leases and the reaper

A claimed turn whose lease lapses is requeued by the reaper with its attempt
count kept and its checkpoints intact, so the next attempt resumes rather than
restarts. The worker that held it, if alive, finds its token refused and its
next heartbeat `CANCELLED`, and stops. Re-running a turn is safe because every
skill derives its work from the artifact and its checkpoints rather than from
anything held in memory, and because every committing write is idempotent by
key, so a retry cannot duplicate one.

---

## Worker protocol

```
loop:
  turn ← POST /v1/turns/claim { roles: [...], worker_id, free_slots }
  if none: sleep(backoff); continue
  materialize working tree if skill.needs_fs
  load skill(turn.skill, turn.skill_version)
  run skill with turn.inputs and turn.checkpoints:
      every model call is validated against the output schema the skill
        declares; a parse or format failure runs the skill's bounded repair
        pass rather than failing the turn
      checkpoint after each declared stage
      heartbeat every N seconds with usage; on anything but CURRENT, stop now
  POST /v1/turns/{id}/complete { result, usage }      -- the one committing write
    or POST /v1/turns/{id}/fail { reason, class, retryable, usage }
```

A worker never invents work: it does what the turn says, with the inputs the
turn carries. It holds nothing between turns, so two workers are
interchangeable and a worker that dies loses at most the work since its last
checkpoint.

A worker registers with the Admin surface (id, roles, skills, model tiers)
so that the queue can report a turn no registered worker can serve — a
`QUEUED` turn past `deadline` with no capable worker is an operator alert,
not a silent stall.

---

## Observability

Per role and per kind: queue depth, oldest queued age, claim latency, turn
duration, attempts per completed turn, checkpoints stored, failure classes,
usage and cost. These feed the `turn_metrics` projection and are
non-governing, except that a turn past `deadline` and a skill stand-down are
surfaced as conditions on the features they hold.

**Who holds the pen.** For every artifact with a live turn against it, the
`pen_holder` projection reports the turn, its kind and skill version, the
worker, the age of its last heartbeat, its checkpoint count, and the budget it
has spent. A stuck turn is then a row a human can read and act on — retry it,
or let it run — rather than an artifact that has simply stopped moving with
nothing to look at. In v6 a claimed task and a crashed agent were
indistinguishable until the lease expired.
