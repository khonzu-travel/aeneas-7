# Workflows — Abandonment

Only a human retires work. The Product Owner abandons a Feature; the Delivery
Lead or Product Owner abandons a task. A reason is required. `[ABANDONED]` is
terminal.

**Feature.** `FeatureAbandoned` on the feature stream: the Spec, Plan, and
every non-`[DONE]` task go to `[ABANDONED]`; every queued turn on the feature
is cancelled and every claimed one has its token refused at its next write;
open clarification sessions, blockers, and review stages close; Data Model
reservations lapse; the feature's citations stop counting; the branch is kept
for audit and excluded from the merge queue; the budget ledger closes. A
feature in `[INTEGRATING]` that has already merged cannot be abandoned — it is
`[DONE]`, and its removal is a new Feature.

**Task.** `TaskAbandoned`: the task and its transitive successors go to
`[ABANDONED]`; their turns are cancelled. The Plan's coverage is now
incomplete, so the platform raises a Defect to the planner naming the
abandoned tasks; the feature cannot integrate until the Plan is revised to
drop or replace them.

**Amendment.** The architect's proposal may be abandoned by either approving
human; a Plan waiting on it returns to the planner with the reason.
