# Platform — Database Schema

PostgreSQL. Five groups: entity tables (aggregate state), version tables
(append-only content), the event store, operational tables (turns, verifier
runs, reservations, frozen paths, blockers, budgets), and projections.
Projections are in [`projections.md`](projections.md); the event store in
[`event-store.md`](event-store.md).

---

## Sequences

```sql
CREATE SEQUENCE feat_seq START 1;   -- F-####
CREATE SEQUENCE amnd_seq START 1;   -- A-####
```

Tasks are numbered per feature (`T###`) from `tasks.md`; the platform assigns
`task_key` at `TasksCreated`.

---

## Entity tables

```sql
CREATE TABLE features (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_number  INTEGER NOT NULL UNIQUE DEFAULT nextval('feat_seq'),
    slug             TEXT NOT NULL,
    priority         INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    feature_type     TEXT NOT NULL CHECK (feature_type IN ('BUSINESS','TECHNICAL')),
    intent           TEXT NOT NULL,
    budget_tokens    BIGINT NOT NULL,
    budget_micros    BIGINT NOT NULL,
    branch           TEXT,
    current_status   TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | DONE | ABANDONED
    stream_seq       INTEGER NOT NULL DEFAULT 0,
    created_by       TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feature_specs (
    feature_id           UUID PRIMARY KEY REFERENCES features(id),
    current_status       TEXT NOT NULL DEFAULT 'DRAFT',
    approved_version_id  UUID,
    rejection_count      INTEGER NOT NULL DEFAULT 0,
    clarify_sessions     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE plans (
    feature_id           UUID PRIMARY KEY REFERENCES features(id),
    current_status       TEXT NOT NULL DEFAULT 'DRAFT',
    approved_version_id  UUID,
    constitution_version_id UUID,           -- the version the approval was checked against
    rejection_count      INTEGER NOT NULL DEFAULT 0,
    analyze_returns      INTEGER NOT NULL DEFAULT 0,
    bug_count            INTEGER NOT NULL DEFAULT 0,
    integration_attempts INTEGER NOT NULL DEFAULT 0,
    write_set            TEXT[] NOT NULL DEFAULT '{}',
    risk_band            TEXT,
    scheduled_at         TIMESTAMPTZ
);

CREATE TABLE tasks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id       UUID NOT NULL REFERENCES features(id),
    task_key         TEXT NOT NULL,                       -- T017
    kind             TEXT NOT NULL CHECK (kind IN ('setup','foundation','test','implement','polish','bug','defect')),
    role             TEXT NOT NULL,
    story            TEXT,                                -- US1
    description      TEXT NOT NULL,
    paths            TEXT[] NOT NULL DEFAULT '{}',
    parallel         BOOLEAN NOT NULL DEFAULT false,
    current_status   TEXT NOT NULL DEFAULT 'PENDING',
    attempt          INTEGER NOT NULL DEFAULT 0,
    UNIQUE (feature_id, task_key)
);

CREATE TABLE task_dependencies (
    predecessor_id UUID NOT NULL REFERENCES tasks(id),
    successor_id   UUID NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (predecessor_id, successor_id),
    CHECK (predecessor_id <> successor_id)
);

CREATE TABLE feature_dependencies (
    predecessor_id UUID NOT NULL REFERENCES features(id),
    successor_id   UUID NOT NULL REFERENCES features(id),
    PRIMARY KEY (predecessor_id, successor_id)
);

CREATE TABLE constitution_meta (
    id                   UUID PRIMARY KEY,
    current_status       TEXT NOT NULL DEFAULT 'DRAFT',
    approved_version_id  UUID,
    semver               TEXT,
    stream_seq           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE amendments (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_number  INTEGER NOT NULL UNIQUE DEFAULT nextval('amnd_seq'),
    level            TEXT NOT NULL CHECK (level IN ('MAJOR','MINOR','PATCH')),
    triggered_by     UUID REFERENCES features(id),
    current_status   TEXT NOT NULL DEFAULT 'DRAFT',
    applied_constitution_version_id UUID
);
```

`data_model`, `data_model_versions`, `data_model_reservations`, and
`plan_entity_refs` are in [`../ledger/data-model.md`](../ledger/data-model.md).

---

## Version tables

All append-only with raise-on-mutation triggers.

```sql
CREATE TABLE spec_versions (
    version_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id  UUID NOT NULL REFERENCES features(id),
    content     TEXT NOT NULL,
    parsed      JSONB NOT NULL,        -- stories, FRs, SCs, markers, clarifications
    turn_id     UUID,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plan_versions (
    version_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id   UUID NOT NULL REFERENCES features(id),
    files        JSONB NOT NULL,       -- { "plan.md": "...", "research.md": "...", "contracts/openapi.yaml": "...", ... }
    parsed       JSONB NOT NULL,       -- capabilities, write set, declarations, citations, tasks, coverage map
    turn_id      UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_verdicts (
    verdict_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id       UUID NOT NULL REFERENCES features(id),
    plan_version_id  UUID NOT NULL REFERENCES plan_versions(version_id),
    reviewer         TEXT NOT NULL,
    decision         TEXT NOT NULL CHECK (decision IN ('APPROVE','REJECT')),
    content          TEXT NOT NULL,
    checklist        JSONB NOT NULL,
    findings         JSONB NOT NULL,
    patch            TEXT,
    turn_id          UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE analyze_reports (
    report_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id       UUID NOT NULL REFERENCES features(id),
    plan_version_id  UUID NOT NULL REFERENCES plan_versions(version_id),
    findings         JSONB NOT NULL,
    coverage         JSONB NOT NULL,
    max_severity     TEXT NOT NULL,
    turn_id          UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE constitution_versions (
    version_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content     TEXT NOT NULL,
    parsed      JSONB NOT NULL,        -- articles, capability map, control catalog, representation contract
    semver      TEXT NOT NULL,
    amendment_id UUID REFERENCES amendments(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE amendment_versions ( … );
CREATE TABLE charter_versions ( … );
CREATE TABLE task_evidence_versions ( … );  -- Bug/Defect evidence, verifier reports as content
```

---

## Operational tables

```sql
CREATE TABLE turns (
    turn_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind               TEXT NOT NULL,
    role               TEXT NOT NULL,
    skill              TEXT NOT NULL,
    skill_version      TEXT NOT NULL,
    stream_type        TEXT NOT NULL,
    stream_id          UUID NOT NULL,
    feature_id         UUID REFERENCES features(id),
    artifact_ref       TEXT NOT NULL,
    trigger_xid        XID8 NOT NULL,
    inputs             JSONB NOT NULL DEFAULT '{}',
    priority           INTEGER NOT NULL,
    not_before         TIMESTAMPTZ NOT NULL DEFAULT now(),
    deadline           TIMESTAMPTZ,
    attempt            INTEGER NOT NULL DEFAULT 0,
    max_attempts       INTEGER NOT NULL DEFAULT 3,
    budget_tokens      BIGINT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','CLAIMED','DONE','FAILED','CANCELLED')),
    worker_id          TEXT,
    lease_expires_at   TIMESTAMPTZ,
    last_heartbeat_at  TIMESTAMPTZ,
    usage              JSONB NOT NULL DEFAULT '{}',
    result             JSONB,
    failure            JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON turns (role, priority, created_at) WHERE status = 'QUEUED';
CREATE INDEX ON turns (lease_expires_at) WHERE status = 'CLAIMED';
CREATE UNIQUE INDEX turns_one_live
    ON turns (stream_id, kind, artifact_ref) WHERE status IN ('QUEUED','CLAIMED');

CREATE TABLE skill_standdowns (
    skill       TEXT NOT NULL,
    reason      TEXT NOT NULL,
    stood_down_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cleared_at  TIMESTAMPTZ,
    cleared_by  TEXT
);

CREATE TABLE verifier_runs (
    run_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id  UUID NOT NULL REFERENCES features(id),
    task_id     UUID REFERENCES tasks(id),          -- NULL for an integration run
    commit      TEXT NOT NULL,
    suite       TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','PASSED','FAILED','INFRA')),
    checks      JSONB NOT NULL DEFAULT '[]',
    risk        JSONB,
    started_at  TIMESTAMPTZ, finished_at TIMESTAMPTZ
);

CREATE TABLE frozen_paths (
    feature_id  UUID NOT NULL REFERENCES features(id),
    path        TEXT NOT NULL,
    task_id     UUID NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (feature_id, path)
);

CREATE TABLE blockers (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id     UUID REFERENCES features(id),
    artifact_ref   TEXT NOT NULL,
    raised_by      TEXT NOT NULL,
    reason         TEXT NOT NULL,
    resume_context JSONB,
    owner_role     TEXT NOT NULL,                      -- the human role that clears it
    cleared_at     TIMESTAMPTZ, cleared_by TEXT, resolution TEXT
);

CREATE TABLE clarification_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id   UUID REFERENCES features(id),
    artifact_ref TEXT NOT NULL,
    version_id   UUID NOT NULL,
    asked_by     TEXT NOT NULL,
    target       TEXT NOT NULL,
    questions    JSONB NOT NULL,
    answers      JSONB,
    applied_version_id UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE decisions (                                -- human sign-offs and acceptances
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id   UUID REFERENCES features(id),
    artifact_ref TEXT NOT NULL,
    version_id   UUID,
    human_role   TEXT NOT NULL,
    human_id     TEXT NOT NULL,
    decision     TEXT NOT NULL,
    reasons      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE usage_ledger (
    id           BIGSERIAL PRIMARY KEY,
    feature_id   UUID REFERENCES features(id),
    turn_id      UUID NOT NULL REFERENCES turns(turn_id),
    model        TEXT NOT NULL,
    tier         TEXT NOT NULL,
    prompt_tokens BIGINT, completion_tokens BIGINT, cached_tokens BIGINT,
    calls INTEGER, duration_ms BIGINT,
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_prices ( engine TEXT, model TEXT, effective_from TIMESTAMPTZ, input_micros BIGINT, output_micros BIGINT, cached_micros BIGINT, PRIMARY KEY (engine, model, effective_from) );

CREATE TABLE processed_requests (
    idempotency_key TEXT PRIMARY KEY,
    result_snapshot JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE projection_checkpoints (
    name        TEXT PRIMARY KEY,
    commit_xid  XID8 NOT NULL DEFAULT '0',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## What is gone from v6

Commission tables and refs; `spec_review_rounds`; the scanning-failure
projection; `notification_outbox`; `projection_active_claims`;
`agent_webhooks`; `archetype` per-subtype rows and `archetype_meta`;
`petitions`; `story_dependencies` and `spec_dependencies` (features depend on
features); `DATA_MODEL_UPDATE` and `AGGREGATE_DELTA` task types; the
`changeDelta` payloads.
