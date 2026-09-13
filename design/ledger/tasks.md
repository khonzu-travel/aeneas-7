# Ledger — Tasks (`tasks.md`)

Tasks are the units of build work. `tasks.md` is authored by the planner as
part of the Plan bundle in Spec Kit's format; when the Plan is approved the
platform creates one task record per line and owns its lifecycle from there.

---

## Format

```markdown
# Tasks: <feature>

**Input**: plan.md@v2, spec.md@v3

## Phase 1 — Setup
- [ ] T001 Create module skeleton at src/billing/__init__.py
- [ ] T002 [P] Add migration scaffold migrations/2026_09_subscriptions.sql

## Phase 2 — Foundational (blocks all user stories)
- [ ] T003 Subscription entity and repository in src/billing/models.py

## Phase 3 — User Story 1: Start a subscription (P1)
**Goal**: ... · **Independent test**: ...
- [ ] T004 [P] [US1] Acceptance tests for US1 scenarios in tests/acceptance/test_subscribe.py
- [ ] T005 [P] [US1] Contract test for POST /subscriptions in tests/contract/test_subscriptions_api.py
- [ ] T006 [US1] Implement SubscriptionService.start in src/billing/service.py
- [ ] T007 [US1] Implement POST /subscriptions in src/api/routes/subscriptions.py
**Checkpoint**: US1 independently verifiable and demoable

## Phase 4 — User Story 2: Cancel a subscription (P2)
...

## Final Phase — Polish
- [ ] T018 [P] Update quickstart.md validation steps

## Dependencies
- T003 blocks T006, T007
- T004, T005 block T006, T007 (tests first)
## Parallel groups
- T004, T005 (different files)
```

Line grammar: `- [ ] T### [P]? [US#]? <description with an exact file path>`.
The platform refuses a line with no path, a `T###` out of sequence, a `[US#]`
naming no story in the spec, or a test task listed after the implementation
task it verifies within the same story.

---

## Task kinds

The platform derives each task's **kind** from its phase and description; the
planner may state it explicitly with a `{kind}` suffix.

| Kind | Role that claims it | Verifier suite | Notes |
|---|---|---|---|
| `setup` | implementer | build, lint | Phase 1 |
| `foundation` | implementer, or `implement-data` for migrations | build, lint, type-check, unit tests, migration dry-run | Phase 2; blocks every story |
| `test` | tester | test files parse and are collected; they **fail** against the current branch | Story phases; authored from spec and contracts; frozen on completion |
| `implement` | implementer (`implement`, `implement-frontend`, `implement-data`) | build, lint, type-check, unit tests, frozen acceptance and contract tests for the story, scanners, write-set check | Story phases |
| `polish` | implementer | build, lint, tests | Final phase |
| `bug` | implementer · `fix` | the failing verifier that raised it, plus the full suite | Raised by the platform after a tester triage; no predecessor |
| `defect` | planner · `defect` | analyze gate on the revised bundle | Raised by triage or by a bound; resolves into a new Plan version and new tasks |

---

## Statuses

| Status | Trigger | Meaning |
|---|---|---|
| `[PENDING]` | Plan approved | Exists; predecessors not all `[DONE]` or the Plan not yet scheduled |
| `[READY]` | Plan `[SCHEDULED]` and every predecessor `[DONE]` | On the board; a turn is enqueued for the claiming role |
| `[CLAIMED]` | a worker claims the task's turn | Work in progress under a lease |
| `[VERIFYING]` | worker signals implementation-complete | The platform runs the verifier suite in a sandbox |
| `[VERIFICATION_FAILED]` | verifier run fails | Returned; `attempt` incremented; a new turn is enqueued with the report, up to `MAX_VERIFY_ATTEMPTS` |
| `[DONE]` | verifier run passes | Successors re-evaluated; `test` tasks freeze their paths |
| `[ABANDONED]` | human decision, or cascade | Terminal; transitive successors cascade |

Blocked is a condition: a task with an open blocker is held out of `[READY]`
and reported `blocked: true`.

---

## Claiming

A task's `[READY]` transition enqueues a turn for its role. Claiming the turn
claims the task; there is no separate task claim signal. When several tasks of
one role are ready across features, turns are ordered by the platform's
**pickup priority**: feature priority, then completion proximity (done / total
tasks of the feature), then unblock count (successors this task releases),
then age. `[P]` tasks of the same story may be claimed concurrently by
different workers; the verifier catches a collision as a write-set or merge
failure on the feature branch, which is why `[P]` is only granted to tasks
naming different files.

---

## Verification

Implementation-complete carries the branch commit the worker produced. The
platform runs the kind's verifier suite against that commit in a sandbox and
records a **verifier report** (`VerifierRunRecorded`): each check, its result,
its output. A pass completes the task. A failure returns it with the report as
the next turn's input. Nothing a worker or a human can do overrides a failed
verifier. See [`../platform/verification.md`](../platform/verification.md).

---

## Bugs and Defects

An acceptance or contract test that fails during a later task's verification,
or at integration, raises a **triage** turn for the tester. Triage answers one
question from the report: does the code diverge from the Plan (→ `bug`, to the
implementer) or does the Plan or Spec have a gap (→ `defect`, to the planner)?
The platform creates the task with the report as its content. Each `bug`
increments the feature's `bug_count`; at `MAX_BUG_RECURRENCE` the platform
raises a `defect` instead and adds a Solution Architect review to the
integration gate. A `defect` resolves into a new Plan version; a version that
changes `data-model.md` reopens the data and architecture reviews before its
new tasks can be `[READY]`.
