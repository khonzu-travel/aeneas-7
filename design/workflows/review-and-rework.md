# Workflows — Review and Rework

How a Plan moves through the analyze gate and the review round, and what a
rejection costs.

```
planner submits bundle v1
  deterministic gates ─ refuse → fix within the turn → resubmit
  [ANALYZING] ─ analyzer turn
     CRITICAL → [REJECTED] (analyze_returns++) → plan.revise → v2 → …
     else → [UNDER_REVIEW] agent stage: review turns in parallel
        each: checklist + findings (+ patch) (+ one bounded session with the planner)
        all decided:
          any REJECT → PlanRejected(all findings, all patches) (rejection_count++) → plan.revise → v2
          all APPROVE → human stage: Solution Architect
             REJECT (reasons) → (rejection_count++) → plan.revise
             APPROVE → PlanApproved, TasksCreated → backlog
```

**Revision.** `plan.revise` starts from the previous version, the analyze
report, every verdict, and every proposed patch. The skill applies patches it
agrees with, argues in `research.md` where it does not, and resubmits the
whole bundle. Reviews on the old version are invalidated; the analyzer runs
again; the agent stage reopens. Reviewers see the diff between versions and
their own previous verdict.

**Bounds.** `MAX_ANALYZE_RETURNS` stops the planner-analyzer loop and hands the
Plan to the Solution Architect with the report. `MAX_PLAN_REJECTIONS` stops
the review loop the same way, with three choices: redirect, Amendment, or
abandon. A redirect is a recorded note the planner revises against and resets
the count.

**What reviewers may not do.** Reject for brevity; ask for elaboration of a
negative determination; ask more than `MAX_REVIEW_QUESTIONS`; leave a checklist
item unanswered; reject without a `HIGH` or `CRITICAL` finding.
