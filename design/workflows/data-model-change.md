# Workflows — Data Model Change

**Feature-driven.** The planner's `data-model.md` cites and declares. At Plan
submit the platform validates declarations, reserves introduced names,
classifies against the current model, and refuses `BREAKING`. The data
reviewer reviews the design; the Solution Architect approves it with the Plan.
At integration the platform re-classifies (the model may have moved) and
transcribes: `DataModelTranscribed`, each document `[APPROVED]` with
`feature_id` and `plan_version_id`. A `BREAKING` result at integration raises a
Defect and refuses the merge; a name that another feature landed first raises
a reservation blocker to the Delivery Lead.

**Defect touching the data design.** A Plan revision in Build that changes a
declaration reopens the data and architecture reviews (and security when a
sensitivity moved); the revised declaration is re-classified and re-reserved;
tasks depending on it wait.

**Independent.** The `reviewer.data` role proposes a new document version
directly (`DataModelChangeProposed`) with the platform-computed classification
and impact list. Reviews: architecture always, security for sensitivity,
Solution Architect for `BREAKING`. Approval transcribes immediately and, for
`BREAKING`, raises a Defect on every live Plan in the impact list so each one
revises its citations.

**Deprecation and retirement.** Deprecation is an independent change that
lists live citing features; retirement is refused while any exist.
