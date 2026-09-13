# Ledger — Data Model

The Data Model is the project's logical data design as approved and built: one
document per entity, per enumeration, and one overview of aggregates and
contexts. It is name-keyed, so the ubiquitous language is a database
constraint.

**Written by**: the platform, transcribing an approved Plan's `data-model.md`
at integration; or the `reviewer.data` role on an independent change
**Read by**: everyone

---

## Two places a data design lives

| Where | What | Authored by | Approved by |
|---|---|---|---|
| A Plan's `data-model.md` | The feature's design: entities cited, entities introduced or revised, as prose and declarations | planner (with the `data-model` skill) | data reviewer, then the Solution Architect with the Plan |
| The project Data Model | The system as approved and built | platform transcription at integration | already approved with the Plan |

Nothing is written to the project Data Model while a feature is unbuilt. The
v6 `DATA_MODEL_UPDATE` task is replaced by the platform doing the
transcription: the declaration was validated, classified, and reviewed at Plan
submit; transcription is a comparison, not authorship, so no turn is needed.

---

## The declaration

Each introduced or revised document in `data-model.md` carries a fenced
`declaration` block satisfying the Constitution's representation contract:

```yaml
declaration:
  kind: ENTITY
  name: Subscription
  intent: INTRODUCE          # or REVISE
  aggregate: Customer
  identity: subscription_id (uuid)
  attributes:
    - name: status
      type: SubscriptionStatus
      required: true
    - name: card_last4
      type: string
      sensitivity: PII
  relationships:
    - to: Customer
      cardinality: many-to-one
  lifecycle: [ACTIVE, PAST_DUE, CANCELLED]
```

The platform reads the declaration for four decisions: classification,
reservation, whether the security reviewer is required (any `sensitivity`
present), and transcription. Prose without a declaration is refused.

---

## Classification

`change_kind` is computed by diffing the declaration against the current
approved document — never asserted:

| `change_kind` | Meaning | At Plan submit | At integration |
|---|---|---|---|
| `ADDITIVE` | New document, or new optional attributes or relationships | accepted | transcribed |
| `STRUCTURAL` | Required attributes, identity, aggregate membership, or lifecycle changed without breaking a citing Plan | accepted; architecture reviewer required | transcribed |
| `BREAKING` | Removes or retypes something a live Plan cites | **refused**, naming the Plans it would break | **refused**; a Defect is raised to the planner |

A breaking change is a decision to invalidate approved work. It travels the
independent path below, where the Solution Architect decides with the impact
list, and the feature's Plan then cites the result.

---

## Reservation and citation

- **Reservation**: a `(kind, name)` introduced by a Plan is reserved from that
  Plan's submit-for-review. A second Plan introducing the same pair is refused,
  naming the holder. The reservation lapses on abandonment or on a Plan
  version that no longer introduces it, and is consumed at transcription.
- **Citation**: every entity a Plan cites must be `[APPROVED]`. Citations are
  recorded and count only while the citing Plan is live, so an abandoned
  feature never holds an entity against retirement.

---

## Statuses (per document)

| Status | Meaning |
|---|---|
| `[APPROVED]` | In force; Plans may cite it. A feature-driven document enters here directly at transcription |
| `[UNDER_REVIEW]` | Independent change awaiting the data reviewer, the architecture reviewer, and, for `BREAKING`, the Solution Architect |
| `[DEPRECATED]` | No new Plan may cite it; existing citations stand and are listed |
| `[RETIRED]` | Nothing live cites it |

---

## Independent changes

A change with no feature behind it — normalization, an aggregate split, a
deprecation, a breaking retype — is proposed by the `reviewer.data` role as a
new document version and reviewed on its own: data and architecture reviewers
always, the security reviewer when a sensitivity classification moves, the
Solution Architect for `BREAKING` with the platform-computed impact list.
Approval transcribes it immediately.

---

## Storage

```sql
CREATE TABLE data_model (
    id             SERIAL PRIMARY KEY,
    kind           TEXT NOT NULL CHECK (kind IN ('OVERVIEW','ENTITY','ENUMERATION')),
    name           TEXT NOT NULL,
    current_status TEXT NOT NULL DEFAULT 'APPROVED',
    UNIQUE (kind, name)
);

CREATE TABLE data_model_versions (
    version_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id      INTEGER NOT NULL REFERENCES data_model(id),
    content          TEXT  NOT NULL,
    declaration      JSONB NOT NULL,
    change_kind      TEXT  NOT NULL CHECK (change_kind IN ('ADDITIVE','STRUCTURAL','BREAKING')),
    feature_id       UUID REFERENCES features(id),          -- NULL on an independent change
    plan_version_id  UUID REFERENCES plan_versions(version_id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT feature_authorization CHECK (
        (feature_id IS NULL AND plan_version_id IS NULL) OR
        (feature_id IS NOT NULL AND plan_version_id IS NOT NULL))
);

CREATE TABLE data_model_reservations (
    kind        TEXT NOT NULL,
    name        TEXT NOT NULL,
    feature_id  UUID NOT NULL REFERENCES features(id),
    PRIMARY KEY (kind, name)
);

CREATE TABLE plan_entity_refs (
    feature_id  UUID    NOT NULL REFERENCES features(id),
    document_id INTEGER NOT NULL REFERENCES data_model(id),
    PRIMARY KEY (feature_id, document_id)
);
```
