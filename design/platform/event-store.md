# Platform — Event Store

The event store is the audit trail and the source of truth for projections.
v7 changes its shape in three ways: events belong to **streams**, writes use
**optimistic concurrency** per stream, and references are **typed columns**.

---

## Schema

```sql
CREATE TABLE events (
    global_seq   BIGINT GENERATED ALWAYS AS IDENTITY,
    stream_type  TEXT NOT NULL CHECK (stream_type IN ('feature','constitution','data_model','platform')),
    stream_id    UUID NOT NULL,
    stream_seq   INTEGER NOT NULL,
    feature_id   UUID,                       -- denormalized for feature-scoped reads
    type         TEXT NOT NULL,
    payload      JSONB NOT NULL DEFAULT '{}',
    turn_id      UUID,                       -- the turn whose signal produced it, if any
    recorded_by  TEXT NOT NULL DEFAULT 'platform',
    commit_xid   XID8 NOT NULL DEFAULT pg_current_xact_id(),
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (global_seq, recorded_at),
    UNIQUE (stream_id, stream_seq, recorded_at)
) PARTITION BY RANGE (recorded_at);

CREATE INDEX ON events (stream_id, stream_seq);
CREATE INDEX ON events (feature_id, global_seq);
CREATE INDEX ON events (type, recorded_at);
CREATE INDEX ON events (commit_xid);
```

Append-only is enforced by `BEFORE UPDATE` and `BEFORE DELETE` triggers that
raise, as in v6. Monthly partitions keep every index shallow and make
archival a partition detach rather than a delete that the trigger would
refuse.

---

## Streams

| Stream type | One per | Holds |
|---|---|---|
| `feature` | Feature | Everything about the Feature: spec, plan, reviews, tasks, verifier runs, blockers, clarifications, turns' completions, integration, release |
| `constitution` | project | Charter, Constitution, Amendments |
| `data_model` | project | Independent Data Model changes; transcriptions are recorded on the feature stream *and* referenced here |
| `platform` | project | Scheduler decisions, worker registry changes, stand-downs, projection rebuilds |

A stream is the unit of ordering and the unit of concurrency control. Every
governed write names exactly one stream.

---

## Optimistic concurrency

```
read  head = max(stream_seq) for stream
validate against entity state (same transaction)
insert event at stream_seq = head + 1
commit
  on unique violation → another writer landed at head + 1: retry from read, ≤ 3 times, then CONFLICT
```

There are no advisory locks. Two writers to different features never touch
the same rows. Two writers to the same feature — a reviewer's verdict landing
while the planner submits a new version — conflict on the unique index, and
the loser re-reads state, at which point its signal may no longer be valid
(`SUPERSEDED`) and is refused with that reason. This is the intended outcome:
the conflict is a real one, and the retry resolves it against fresh state.

The entity tables (`features`, `feature_specs`, `plans`, `tasks`, …) carry a
`stream_seq` column updated with every write, so "the state at event N" is
answerable and the gate's read is provably the head it wrote against.

---

## Global ordering for consumers

`global_seq` is monotonic but not gap-safe under concurrent commits: a
transaction can take a lower number and commit later. Projectors therefore
cursor on `commit_xid`, which is safe by construction:

```sql
SELECT * FROM events
WHERE commit_xid > $checkpoint
  AND commit_xid < pg_snapshot_xmin(pg_current_snapshot())
ORDER BY commit_xid;
```

Every transaction with an xid below the snapshot's `xmin` has finished, so no
row can later appear below the watermark. Per-stream order is preserved: a
write at `stream_seq n+1` read `n` committed, so its xid was assigned after
`n`'s. `global_seq` remains the human-facing position.

---

## Event taxonomy

Payloads carry version ids and the fields named; artifact identity is in the
typed columns.

### Feature stream

| Event | Payload | Recorded when |
|---|---|---|
| `FeatureCreated` | `key`, `priority`, `budget`, `intent` | Product Owner submits intent |
| `SpecVersionSubmitted` | `version_id`, `turn_id` | analyst submits a version |
| `ClarificationOpened` / `ClarificationAnswered` / `ClarificationApplied` | `session_id`, `target`, `questions[]` / `answers[]` / `version_id` | a session moves |
| `SpecSubmittedForReview` / `SpecApproved` / `SpecRejected` | `version_id`; `reasons[]` on rejection | the spec moves |
| `PlanVersionSubmitted` | `version_id`, `files[]`, `write_set[]`, `declarations[]`, `citations[]`, `capabilities[]` | planner submits the bundle |
| `PlanSubmittedForReview` | `version_id`, `gates_passed[]` | deterministic gates green |
| `PlanAnalyzed` | `version_id`, `report_id`, `max_severity`, `coverage` | the analyze turn completes |
| `ReviewStageOpened` | `stage` (`agent` \| `human`), `reviewers[]`, `version_id` | a stage opens |
| `ReviewRecorded` | `reviewer`, `decision`, `verdict_id`, `version_id` | a verdict or human decision |
| `ReviewsInvalidated` | `version_id`, `previous_version_id`, `change_summary` | a new version during review |
| `PlanApproved` / `PlanRejected` | `version_id`; `findings[]` | the stage closes |
| `TasksCreated` | `tasks[]` (`key`, `kind`, `role`, `paths[]`, `story`, `predecessors[]`) | Plan approved |
| `PlanScheduled` / `PlanHeld` | `reason` (`WIP`, `WRITE_SET_CONFLICT:F-0031`, `PREDECESSOR:F-0031`, `BLOCKED`) | scheduler decision |
| `TaskReady` / `TaskClaimed` / `TaskImplementationComplete` | `task_id`; `turn_id`; `commit` | task lifecycle |
| `VerifierRunRecorded` | `task_id`, `run_id`, `commit`, `checks[]`, `passed` | every run |
| `TaskCompleted` / `TaskVerificationFailed` | `task_id`, `run_id`, `attempt` | outcome |
| `PathsFrozen` | `task_id`, `paths[]` | a `test` task completes |
| `BugRaised` / `DefectRaised` | `task_id`, `from_run_id`, `triage_turn_id`, `evidence_version_id` | triage |
| `BugRecurrenceLimitReached` | `bug_count`, `defect_task_id` | bound |
| `BlockerRaised` / `BlockerCleared` | `blocker_id`, `artifact`, `reason`, `resume_context`; `cleared_by`, `resolution` | blockers |
| `IntegrationStarted` / `IntegrationSucceeded` / `IntegrationFailed` | `attempt`, `base_commit`; `merge_commit`, `risk`; `reason` | merge queue |
| `RiskAssessed` | `score`, `band`, `signals{}` | integration verifier run |
| `RiskAccepted` | `decided_by`, `band` | Solution Architect decision |
| `DataModelTranscribed` | `documents[]` (`kind`, `name`, `version_id`, `change_kind`) | integration |
| `DeploymentStarted` / `DeploymentCompleted` / `DeploymentFailed` | `environment`, `commit`; `reason` | release |
| `FeatureCompleted` | — | released and healthy |
| `FeatureAbandoned` / `TaskAbandoned` | `reason`, `decided_by`, `cascade[]` | human decision |
| `TurnEnqueued` / `TurnCompleted` / `TurnFailed` / `TurnCancelled` | `turn_id`, `kind`, `role`, `skill`, `skill_version`; `usage`; `reason`, `class` | the queue |
| `BudgetExhausted` | `spent`, `budget` | bound |
| `StatusTransitioned` | `artifact`, `from`, `to`, `trigger_seq` | every status change |

### Constitution stream

`CharterOnboarded`, `CharterVersionSubmitted`, `CharterApproved`,
`ConstitutionVersionSubmitted`, `ConstitutionSubmittedForReview`,
`ConstitutionApproved`, `ConstitutionRejected`, `AmendmentProposed`,
`AmendmentSubmittedForReview`, `AmendmentApproved`, `AmendmentRejected`,
`AmendmentApplied` (`constitution_version_id`, `affected_features[]`).

### Data Model stream

`DataModelChangeProposed`, `DataModelChangeApproved`, `DataModelChangeRejected`,
`DataModelDocumentDeprecated`, `DataModelDocumentRetired`, plus a reference
row `DataModelTranscribed` mirroring the feature event.

### Platform stream

`WorkerRegistered`, `SkillVersionPublished`, `SkillStoodDown`,
`SkillStandDownCleared`, `ProjectionRebuilt`, `SchedulerPolicyChanged`.

---

## Reading the audit trail

Feature history is one query:

```sql
SELECT stream_seq, type, payload, recorded_by, recorded_at
FROM events WHERE stream_id = $feature ORDER BY stream_seq;
```

The version a decision pinned:

```sql
SELECT pv.* FROM events e
JOIN plan_versions pv ON pv.version_id = (e.payload->>'version_id')::uuid
WHERE e.stream_id = $feature AND e.type = 'PlanApproved';
```

Cross-feature questions ("every `BREAKING` refusal this month") are
projections, not scans.
