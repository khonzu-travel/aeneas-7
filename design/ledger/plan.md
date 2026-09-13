# Ledger — Plan (the `plan.md` bundle)

The Plan is the execution design for one feature: how the approved Feature Spec
is realized within the Constitution. It replaces the v6 Spec and takes Spec
Kit's plan bundle shape. One planner turn authors the whole bundle; specialist
roles review it in one parallel round.

**Owner**: `planner` role
**Reviewers**: `reviewer.architecture`, `reviewer.data`, `reviewer.security`, `reviewer.ux` (when the feature has UI)
**Approver**: Solution Architect

---

## The bundle

| File | Content | Read by the platform for |
|---|---|---|
| `plan.md` | Summary; Technical Context; **Constitution Check**; **Required Capabilities**; Project Structure; **Write Set**; Complexity Tracking; Risks | capability check, write-set scheduling, analyze gate |
| `research.md` | Decisions made to resolve `NEEDS CLARIFICATION` in the technical context: decision, rationale, alternatives | analyze gate (no unresolved items) |
| `data-model.md` | Entities cited and entities introduced or revised, as prose **and** machine-readable declarations satisfying the representation contract | citation, reservation, classification, transcription |
| `contracts/` | API contracts (OpenAPI, GraphQL SDL, event schemas) for every interface the feature exposes or changes | contract tests, surface-change signal in the risk score |
| `quickstart.md` | The validation scenarios a reviewer or verifier walks to confirm the feature works, as executable steps | verifier assertions |
| `threat-model.md` | Threat surfaces engaged (or determined not engaged), threats, controls, and the `controlCoverage` block against the Constitution's control catalog | security verifier, risk score |
| `checklists/` | `requirements.md` (spec quality), plus per-reviewer rubrics the review round answers | review verdict structure |
| `tasks.md` | The task list — see [`tasks.md`](tasks.md) | task records, coverage |

The bundle is versioned as a whole. A revision resubmits every file.

---

## `plan.md` format

```markdown
# Implementation Plan: <feature>

**Feature**: F-0042 · **Spec**: spec.md@v3 · **Constitution**: 1.3.0 · **Date**: 2026-09-12

## Summary
<primary requirement and the technical approach, three to five sentences>

## Technical Context
**Language/Version**: ... · **Dependencies**: ... · **Storage**: ... · **Testing**: ...
**Target platform**: ... · **Project type**: ... · **Performance goals**: ...
**Constraints**: ... · **Scale/Scope**: ...

## Constitution Check
| Article | Status | Note |
|---|---|---|
| I — ... | PASS | ... |
| III — Test-first | PASS | acceptance tests in T004–T009 precede implementation |
| VII — Simplicity | JUSTIFIED | see Complexity Tracking |

## Required Capabilities
- CAP-AUTH
- CAP-NOTIFY

## Project Structure
### Documentation
### Source code
<the concrete tree this feature adds to or changes>

## Write Set
- `src/billing/**`
- `src/api/routes/subscriptions.py`
- `migrations/2026_09_*.sql`
- `web/app/(account)/subscriptions/**`

## Complexity Tracking
| Violation | Why needed | Simpler alternative rejected because |

## Risks
- ...
```

**Constitution Check** must list every Article with `PASS`, `JUSTIFIED`
(with a Complexity Tracking row), or `FAIL`; a `FAIL` refuses submission.
**Required Capabilities** lists identifiers copied from the Constitution's
Capability Map; an unknown identifier refuses the version. **Write Set** is a
list of path globs; the scheduler and the verifier read it.

---

## Proportionality

A section the feature does not engage is settled by a one-line negative
determination, never omitted and never elaborated. `threat-model.md` is
always present: it names every threat surface in the Constitution with a
determination. A reviewer never rejects for brevity; it rejects for a wrong
determination or a missing thing a build turn would need.

---

## Statuses

| Status | Trigger | Meaning |
|---|---|---|
| `[DRAFT]` | `SpecApproved` enqueues a `plan` turn; a rejection or an analyze return | The planner is authoring or revising |
| `[ANALYZING]` | planner submit-for-review; format, capability, and data-model gates pass | The analyze gate is running (deterministic passes, then an `analyzer` turn) |
| `[UNDER_REVIEW]` | analyze gate passes | Agent stage: reviewers hold open decisions; then human stage: the Solution Architect |
| `[APPROVED]` | all decisions approved | Version pinned; task records created; Data Model reservations confirmed; the feature enters the backlog |
| `[REJECTED]` | any reviewer rejects (stage closes when all have decided) or analyze returns `CRITICAL` | Returned to the planner with every finding and patch; `rejection_count` incremented (analyze returns count separately) |
| `[SCHEDULED]` | the scheduler releases it | Tasks with no predecessors are `[READY]` |
| `[IN_BUILD]` | first task claimed | Build in progress |
| `[INTEGRATING]` | all tasks `[DONE]` | In the merge queue |
| `[DONE]` | integrated and released | — |
| `[ABANDONED]` | cascade from the Feature | Terminal |

---

## The review round

When the analyze gate passes, the platform enqueues one review turn per
required reviewer, in parallel. Each returns a **verdict**:

```markdown
# Review: reviewer.data · plan@v2

**Decision**: APPROVE | REJECT
## Checklist
- [x] R1 Every cited entity resolves against the Data Model
- [ ] R4 Every introduced attribute carries a sensitivity classification — Subscription.card_last4 is unclassified
## Findings
| ID | Severity | Location | Summary | Recommendation |
|---|---|---|---|---|
| D1 | HIGH | data-model.md#Subscription | card_last4 unclassified | classify as PII, restricted |
## Proposed patch
```diff
--- data-model.md
+++ data-model.md
@@ ... @@
-  - card_last4: string
+  - card_last4: string, sensitivity: PII
```
```

A checklist item left unanswered refuses the verdict. A `REJECT` must carry at
least one `HIGH` or `CRITICAL` finding. A reviewer that needs an answer asks
through a bounded clarification session targeting the planner
(`MAX_REVIEW_QUESTIONS`), then decides. The stage closes when every reviewer
has decided; the planner revises against the whole round and the patches at
once. Sign-off invalidation on a new version reopens the agent stage.

---

## Relationship to other artifacts

- **Feature Spec**: the Plan maps every `FR-###` and every user story; the
  coverage check refuses a submission that leaves one unmapped.
- **Constitution**: the Constitution Check and Required Capabilities are
  the referencing end; an Amendment applied while the Plan is open enqueues
  a re-analyze turn.
- **Data Model**: `data-model.md` cites and declares; the platform reserves,
  classifies, and at integration transcribes. See [`data-model.md`](data-model.md).
- **Tasks**: `tasks.md` is part of the bundle and is approved with it.
