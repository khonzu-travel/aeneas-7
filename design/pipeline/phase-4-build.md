# Pipeline — Phase 4: Build

**Purpose**: implement the Plan as tasks, each verified by the platform.
**Roles**: `tester`, `implementer`; `planner` for Defects.
**Input**: Plan at `[SCHEDULED]`, tasks `[READY]`.
**Output**: every task `[DONE]`; Plan at `[INTEGRATING]`.

---

## The task loop

```
TaskReady ─▶ turn enqueued for the task's role
   ─▶ worker claims the turn (= claims the task), materializes the branch
   ─▶ skill works: reads the bundle under specs/, writes code/tests, commits
   ─▶ implementation-complete { commit }
   ─▶ [VERIFYING]: platform runs the kind's suite in a sandbox
        pass ─▶ [DONE]; successors evaluated; test tasks freeze their paths
        fail ─▶ [VERIFICATION_FAILED]; attempt++ ; re-enqueue with the report
               at MAX_VERIFY_ATTEMPTS ─▶ Defect to the planner with the reports
```

Tests come first by construction: `tasks.md` lists each story's `test` tasks
before its `implement` tasks and the platform refuses the reverse; the `test`
suite requires the new tests to fail on the branch; the tests are frozen when
the task completes; an implementer diff touching them fails.

---

## Roles in the phase

**tester** (`test` tasks): authors acceptance tests from the spec's
Given/When/Then scenarios and contract tests from `contracts/`, using only
those and `quickstart.md`. It never reads implementation, and by ordering
there is none to read. On `triage` turns it reads a verifier report and
decides Bug or Defect.

**implementer** (`setup`, `foundation`, `implement`, `polish`, `bug` tasks):
implements exactly what the Plan and the task say, within the write set, with
unit tests. It reads the spec scenarios because the frozen tests were written
from them. It raises a blocker when the Plan is ambiguous rather than
deciding; a wrong Plan is a Defect, raised through triage when a test exposes
it, or directly by the implementer with evidence.

**planner** (`defect` tasks): revises the bundle. A revision that changes
`data-model.md` or `contracts/` reopens the data, architecture, and (for
sensitivity changes) security reviews before its new tasks are `[READY]`; any
other revision re-runs the analyze gate only. New or changed tasks are added
to `tasks.md` with fresh keys; tests for changed scenarios are re-authored by
a new `test` task, which re-freezes them.

---

## Parallelism

Tasks marked `[P]` in the same phase name different files and may be claimed
by different workers at once. Foundational tasks block every story. Stories
are independent slices: with capacity, P1's tasks and P2's tasks run
concurrently once the foundation is `[DONE]`. Pickup priority across
features: feature priority, completion proximity, unblock count, age.

---

## Bugs and Defects

An acceptance or contract test that passed at its task and fails later (a
later task on the branch, or integration) is a regression; the platform
enqueues `task.triage`. The tester's verdict raises a `bug` (implementer,
`fix` skill, the failing check as its verifier) or a `defect` (planner). Each
`bug` counts toward `MAX_BUG_RECURRENCE`; at the bound the platform raises a
`defect` instead and marks the feature for a Solution Architect review at
integration.

---

## Phase gate

When every task is `[DONE]`, no blocker is open, and no Bug or Defect is open,
the Plan transitions to `[INTEGRATING]` and enters the merge queue.
