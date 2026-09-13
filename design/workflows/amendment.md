# Workflows — Amendment

```
trigger: analyze gate finds a Constitution gap (CRITICAL: capability not granted / Article conflict)
         or the architect proposes independently
platform enqueues amend.author (architect); the triggering Plan waits at [DRAFT] with waiting_on: amendment
architect turn: proposes A-#### with the diff, the level, and the impact list (computed by the platform
   from Required Capabilities and Constitution Checks of every open Plan)
submit → [UNDER_REVIEW]: Solution Architect and Enterprise Architect decide
   both APPROVE → applied in the same transaction: new Constitution version, semver bumped,
                  AmendmentApplied(affected_features[]), [APPLIED]
                  → plan.analyze enqueued for every affected open Plan
                  → the triggering Plan resumes: plan.revise enqueued
   either REJECT → [REJECTED]; the triggering Plan is [REJECTED] with the reason;
                  the planner revises within the Constitution, or the analyst revises the spec,
                  or the Product Owner abandons
```

A Plan already in Build whose re-analysis returns `CRITICAL` is held at the
integration gate for the Solution Architect, who accepts it against the old
Constitution version (recorded) or sends it back as a Defect.
