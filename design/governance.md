# Governance

Rules the platform enforces. A rule a skill could ignore is not on this page.

---

## Rules

| Rule | Enforcement |
|---|---|
| **Platform-Owned Transitions** | No API accepts a status. Every transition is executed by the Custodian in response to a validated signal, recorded as an event on the artifact's stream, and mirrored on the entity table |
| **Sole Writer** | Workers and the UI hold no database credentials. All writes pass through the Custodian |
| **Turn Scope** | Every worker write carries a turn token naming `turn_id`, `role`, `feature_id`, and expiry. A write outside that scope, or after expiry, is refused |
| **Single Committing Write** | A turn performs any number of reads and exactly one committing write. A second is refused, naming the write that landed. Checkpoints and heartbeats are exempt because they change no governed state. A turn therefore cannot leave an artifact half-created |
| **Whole-Artifact Submission** | An artifact is submitted entire — the Plan bundle with its `tasks.md`, the spec with its sections — never assembled by successive calls. This is what makes Single Committing Write affordable |
| **One Live Turn** | At most one `QUEUED` or `CLAIMED` turn exists per `(stream, kind, artifact)`, enforced by a partial unique index. A duplicate enqueue is a no-op, so no artifact is ever authored twice concurrently |
| **Currency** | A turn learns at its heartbeat that it is superseded or cancelled, and its completion is refused with that reason. Work does not continue against an artifact that has moved |
| **Append-Only Audit** | `events` and every content version table reject `UPDATE` and `DELETE` by trigger |
| **ID Issuance** | Identifiers (`F-####`, `T###` within a feature, `A-####`) are issued by the platform from sequences. A worker that supplies one is refused |
| **Format Conformance** | A submitted `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, or `constitution.md` is parsed against its template. A missing required section, an unnumbered requirement, a task without a file path, or an unresolved `[NEEDS CLARIFICATION]` at submit-for-review is refused with the location |
| **Constitution Supremacy** | A Plan that relies on a capability, technology, or pattern the Constitution does not declare, or that violates a `MUST` Article, is refused at submit by the analyze gate's deterministic pass and again by its consistency pass as `CRITICAL`. A gap is closed by an Amendment, never by a line in the Plan |
| **Coverage** | At submit, every `FR-###` maps to at least one `T###`, every user story to at least one acceptance scenario and one task, every `SC-###` to a verifier assertion or a checklist item. Unmapped items refuse the submission |
| **Data Model Citation** | Every entity a Plan cites exists in the Data Model at `[APPROVED]`; a citation of a deprecated or retired document is refused with the reason |
| **Data Model Reservation** | A `(kind, name)` a Plan introduces is reserved from its submit-for-review; a second Plan introducing the same pair is refused, naming the holder. The reservation lapses on abandonment or on a version that drops it, and is consumed at integration |
| **Data Model Classification** | `change_kind` (`ADDITIVE`, `STRUCTURAL`, `BREAKING`) is computed by the platform from the declaration diff, at submit and again at integration. `BREAKING` is refused at both; it travels the Data Model's independent review with an impact list |
| **Test Independence** | Acceptance and contract tests are authored by a `tester` turn from the Feature Spec and `contracts/` and frozen when that task completes. An implementer diff touching a frozen path fails verification |
| **Verified Completion** | No task completes on a worker's signal. Implementation-complete starts the task's verifier suite in a sandbox; only a passing run completes the task. A failing run is not human-overridable |
| **Approved Before Build** | A task is claimable only when its feature's Plan is at `[SCHEDULED]` or `[IN_BUILD]` and every predecessor task is `[DONE]` |
| **Write-Set Discipline** | A Plan declares its write set. An implementer diff outside it fails verification unless the task's entry in `tasks.md` names the path; the scheduler holds a feature whose write set overlaps a feature in Build when the policy is `strict` |
| **Serialized Integration** | One feature integrates onto the trunk at a time. Integration requires a green full verifier run on the rebased branch and, for `MEDIUM`/`HIGH` risk, a recorded Solution Architect decision |
| **Governed Constitution Change** | Constitution content changes only by applying an `[APPROVED]` Amendment, exactly once; the platform transitions the Amendment to `[APPLIED]` in the same transaction and enqueues a re-analyze turn for every Plan not yet integrated |
| **Governed Abandonment** | Only a human retires work: the Product Owner a Feature, the Delivery Lead or Product Owner a task. A reason is required; the cascade is strictly downward; `[ABANDONED]` has no edge out |
| **Bounded Loops** | Every loop bound below is a platform counter checked at the signal; reaching it refuses the next iteration and enqueues the declared escalation |
| **Budgeted Features** | Every turn reports usage; the platform fails a turn at its turn budget and raises a `BUDGET_EXHAUSTED` blocker at the feature budget. Nothing else in the decision path reads a cost |
| **Bounded Intake** | Features not yet terminal are capped at `MAX_OPEN_FEATURES`; intent past the cap is queued as `PENDING_INTAKE` with its position. Backpressure exists before Build, not only at the scheduling gate |
| **No Self-Remediation** | The `operator` role writes anomaly records only. A production change is a new Feature |

---

## Loop bounds

| Bound | Counted on | Default | On reaching it |
|---|---|---|---|
| `MAX_CLARIFY_SESSIONS` | Feature Spec, per version lineage | 3 | The analyst submits with stated assumptions; the Product Owner decides on them |
| `MAX_CLARIFY_QUESTIONS` | Per session | 5 | Session closes |
| `MAX_SPEC_REJECTIONS` | Feature Spec | 3 | Feature held; Product Owner chooses revise-intent or abandon |
| `MAX_REVIEW_QUESTIONS` | Per reviewer per Plan version | 2 | Reviewer decides on what is present |
| `MAX_PLAN_REJECTIONS` | Plan | 3 | Plan held; Solution Architect chooses redirect, Amendment, or abandon |
| `MAX_ANALYZE_RETURNS` | Plan version lineage | 3 | Plan held for the Solution Architect with the analyze report; the planner is not re-run |
| `MAX_VERIFY_ATTEMPTS` | Per task | 3 | Task held; a Defect is raised to the planner carrying the verifier reports |
| `MAX_BUG_RECURRENCE` | Per feature | 3 | The platform raises a Defect instead of a Bug and adds a Solution Architect review to the integration gate |
| `MAX_INTEGRATION_ATTEMPTS` | Per feature | 2 | Blocker to the Delivery Lead with the conflict report |
| `MAX_TURN_ATTEMPTS` | Per turn | 3 | Turn `[FAILED]`; the failure is visible in the queue and retryable by the Delivery Lead |
| `TURN_BUDGET` | Per turn, from the skill | skill-defined | Turn `[FAILED]` with `BUDGET` |
| `FEATURE_BUDGET` | Per feature, from intent capture | project default | `BUDGET_EXHAUSTED` blocker to the Product Owner, who raises the budget or abandons |
| `MAX_BUILD_WIP` | Features in Build | project default | Scheduler holds |
| `MAX_OPEN_FEATURES` | Features not `[DONE]` or `[ABANDONED]` | project default | New intent is queued as `PENDING_INTAKE` |
| `MAX_REPAIR_PASSES` | Per model call within a turn | 2 | The turn fails `TRANSIENT` with the invalid output attached; the next attempt resumes from the last checkpoint |
| `MAX_CHECKPOINTS`, `MAX_CHECKPOINT_BYTES` | Per turn, from the skill | skill-defined | The checkpoint write is refused; the turn continues |

---

## System invariants

The platform halts a feature's progression and surfaces the condition if any
of these is false.

1. Every integrated change traces to a `[DONE]` task, to an `[APPROVED]` Plan version, to an `[APPROVED]` Feature Spec version, to a recorded intent.
2. Every Plan approved conforms to the Constitution version current at its approval, and every Plan not yet integrated has been re-analyzed against every Amendment applied since.
3. Every stream is gap-free: `stream_seq` is contiguous per stream.
4. No task is `[CLAIMED]` or `[VERIFYING]` with a predecessor not `[DONE]`.
5. Every `[DONE]` task has a passing verifier run recorded against the version it completed.
6. No acceptance-test path frozen for a feature differs between the tester's completing version and the integrated version.
7. Every Data Model version traces to the approved Plan version whose declaration it transcribes, or to its own recorded review.
8. No two Plans past submit-for-review introduce the same `(kind, name)`.
9. Every turn token ever honored named a turn that was `[CLAIMED]` at the time.
10. No turn has more than one committing write recorded against it.
11. No `(stream, kind, artifact)` has two live turns against it.
12. Every applied Amendment corresponds to exactly one Constitution version.
13. No feature exceeds `FEATURE_BUDGET` without a `BUDGET_EXHAUSTED` blocker recorded.

---

## Principles

**The platform is the loop harness.** Generators are skills; verifiers, bounds,
stops, and escalations belong to the platform. A skill can be wrong; the loop
around it cannot be skipped.

**Governance is structural.** If a rule can be bypassed by ignoring an
instruction, it is not governed. Instructions live in skills and shape quality;
rules live in the Custodian and shape what is possible.

**Formats are verifiers.** A fixed, numbered artifact format is the cheapest
verifier there is: it makes coverage, ambiguity, and conformance computable.

**Roles are permissions, workers are capacity.** Separation of duties is a
property of turns, not of processes.

**Streams isolate; the merge queue serializes.** Features never wait on each
other in the database. They wait on each other only where they truly share
something — a name, a principle, a file — and each of those has one explicit
rule.

**Self-assessment is telemetry.** What a worker says about its own work is
recorded and never decides anything. What the verifier says decides.

**A turn is the unit the platform can see.** Because work is a row the
platform issues, leases, and closes, it can be deduplicated, resumed,
budgeted, cancelled, and shown to a human. Every property this design relies
on for reliability under load — one live turn per artifact, one committing
write, resume from checkpoint, stop when superseded, a visible pen holder —
follows from the platform knowing what a unit of work is. v6's repairs were
agent-side guards for a unit the platform could not see.

**Humans approve intent and accept risk.** Product Owners approve what is to be
built; Solution Architects approve how and accept high-risk integrations;
Enterprise Architects approve the constitution. Everything else is a machine
gate, and humans see it only when a bound is reached.
