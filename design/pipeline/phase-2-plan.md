# Pipeline — Phase 2: Plan

**Purpose**: turn an approved Feature Spec into an approved Plan bundle with
tasks, in as few turns as the work allows.
**Roles**: `planner`; `analyzer`; `reviewer.architecture`, `reviewer.data`,
`reviewer.security`, `reviewer.ux`; the Solution Architect approves.
**Input**: `spec.md` at `[APPROVED]`.
**Output**: the Plan bundle at `[APPROVED]`; task records created.

---

## Flow

1. `SpecApproved` enqueues `plan.author`. A planner turn runs the `plan`
   skill: it reads the spec, the Constitution, and the Data Model; resolves
   its technical context (writing `research.md` for every decision); authors
   `plan.md` with the Constitution Check, Required Capabilities, Project
   Structure, and Write Set; runs the `data-model`, `contracts`,
   `threat-model`, and `quickstart` sub-skills to produce the companion
   files; runs the `tasks` skill to produce `tasks.md`; runs the requirements
   checklist; and submits the bundle as one version. A planner that needs a
   meaning it cannot resolve opens a clarification session with the analyst
   rather than guessing.
2. **Deterministic gates** run at submit: format, capabilities, Constitution
   Check, coverage, data-model citation/reservation/classification, write set,
   markers. A refusal names the location; the turn fixes and resubmits within
   the same turn budget.
3. `PlanSubmittedForReview` → `[ANALYZING]`; the platform enqueues
   `plan.analyze`. The analyzer turn runs the consistency pass and records
   `PlanAnalyzed`. `CRITICAL` → `[REJECTED]` with the report; `plan.revise`
   enqueued; `analyze_returns` up (bounded by `MAX_ANALYZE_RETURNS`).
4. Otherwise `[UNDER_REVIEW]`, agent stage: the platform enqueues one review
   turn per required reviewer **in parallel** — architecture, data, security
   always; UX when `tasks.md` has a frontend implementation task. Each
   reviewer runs its skill against its checklist and the analyze report and
   returns a verdict (checklist, findings, optional patch). A reviewer may
   open one bounded session with the planner (`MAX_REVIEW_QUESTIONS`) when
   the Plan is silent; it rejects when the Plan is wrong.
5. The stage closes when every reviewer has decided. Any `REJECT` →
   `PlanRejected` carrying every finding and patch; `[REJECTED]`;
   `rejection_count` up; `plan.revise` enqueued. All `APPROVE` →
   `ReviewStageOpened(human)`; the Solution Architect's inbox gains the
   decision with the bundle, the analyze report, and the verdicts.
6. The Solution Architect approves (`PlanApproved`, version pinned,
   `TasksCreated`, reservations confirmed, the feature enters the backlog) or
   rejects with reasons.
7. A revision resubmits the whole bundle; reviews on the previous version are
   invalidated and the agent stage reopens. At `MAX_PLAN_REJECTIONS` the Plan
   is held for the Solution Architect: redirect (a note the planner revises
   against, count reset), propose an Amendment (a Constitution gap), or
   abandon.

---

## Turn count

| Path | Turns |
|---|---|
| Clean | planner 1 + analyzer 1 + reviewers 3–4 (parallel) = 5–6, then one human decision |
| One review round of findings | + planner 1 + analyzer 1 + reviewers 3–4 |
| Analyze return | + planner 1 + analyzer 1 |

The v6 equivalent with three Commissions was roughly thirteen turns and eight
serialized hops before a reviewer read anything.

---

## Reviewer checklists

Each reviewer skill ships a checklist; the platform refuses a verdict with an
unanswered item.

| Reviewer | Checks |
|---|---|
| architecture | Constitution Check is honest; Required Capabilities are the ones used; module boundaries and patterns conform; write set is complete and minimal; Complexity Tracking justifies every `JUSTIFIED` |
| data | every citation resolves; every declaration satisfies the representation contract; classification matches the design; sensitivity is declared on every attribute that needs it; migrations are reversible or say why not |
| security | every threat surface in the Constitution has a determination; controls map to the catalog; `controlCoverage` is complete; contracts expose nothing the spec does not require; dependencies are vetted |
| ux | every UI story has states, errors, and accessibility per the Constitution's conventions; scenarios are implementable as written |

---

## Constraints

- A Plan cannot enter review with an open clarification session, an unmapped
  requirement, an unknown capability, or a `BREAKING` declaration.
- Reviewers never reject for brevity; a negative determination is an answer.
- A Constitution gap is an Amendment, never a line in the Plan; the Plan
  waits at `[DRAFT]` with `waiting_on: amendment` and resumes on application.
- The Solution Architect is never asked before every machine and agent gate
  has passed.
