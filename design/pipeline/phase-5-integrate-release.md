# Pipeline — Phase 5: Integrate & Release

**Purpose**: land the feature on the trunk safely and deploy it.
**Roles**: `integrator`; the Solution Architect accepts `MEDIUM`/`HIGH` risk;
the Delivery Lead clears integration blockers.
**Input**: Plan at `[INTEGRATING]`.
**Output**: `DeploymentCompleted` healthy; Feature `[DONE]`.

---

## Integration

The merge queue processes one feature per repository at a time (see
[`../platform/concurrency.md`](../platform/concurrency.md)):

1. `IntegrationStarted` records the trunk base. An `integrate` turn rebases
   the feature branch onto it, resolving conflicts only within the write set
   (a conflict outside it is an integration failure), and pushes.
2. The verifier runner executes the full suite on the rebased commit: the
   whole trunk's tests plus every frozen test of the feature, all scanners,
   and the risk score. `RiskAssessed` records the band with its signals.
3. `LOW`: the platform fast-forwards the trunk. `MEDIUM`/`HIGH`, or a feature
   that reached `MAX_BUG_RECURRENCE`: the Solution Architect's inbox gains a
   risk acceptance with the diff, the signals, and the report; the feature
   steps aside from the lock and re-verifies if the trunk moved before the
   decision. `RiskAccepted` merges; a rejection raises a blocker to the
   Delivery Lead with the Solution Architect's reasons (a rejected
   integration usually becomes a Defect).
4. On merge: `DataModelTranscribed` writes the Plan's declarations into the
   project Data Model (classification recomputed; `BREAKING` here raises a
   Defect and refuses the merge); `IntegrationSucceeded`; `release` enqueued.

Failures re-enqueue up to `MAX_INTEGRATION_ATTEMPTS`, then a blocker to the
Delivery Lead with the report.

---

## Release

A `release` turn runs the `release` skill: it deploys the merged commit
through the project's pipeline to the environment the Constitution's
Operational Model names, verifies health, and signals `DeploymentCompleted`
(→ Feature `[DONE]`, Spec `[DONE]`) or `DeploymentFailed` with the reason
(→ blocker to the Delivery Lead; the release skill rolls back per the
Operational Model, and the rollback is recorded). Release never re-opens Build:
a failed release that needs code is a new Feature or a Defect decided by the
Delivery Lead.
