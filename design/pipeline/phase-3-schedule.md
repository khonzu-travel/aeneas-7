# Pipeline — Phase 3: Schedule

**Purpose**: release approved Plans into Build in the right order without
collisions.
**Roles**: the platform scheduler; the Delivery Lead may override.
**Input**: Plan at `[APPROVED]`.
**Output**: Plan at `[SCHEDULED]`, its branch created, its first tasks `[READY]`.

---

## Why no agent

v6 notified a Scrum Master agent, which read the backlog and signaled a
decision the platform then validated against rules it already held. The rules
are deterministic. v7 evaluates them directly on every event that can change
the answer, and gives a human the override.

---

## Evaluation

Triggered by `PlanApproved`, `FeatureCompleted`, `FeatureAbandoned`,
`BlockerCleared`, `IntegrationSucceeded`, and a Delivery Lead decision. For
each `[APPROVED]` Plan in priority order:

| Condition | Held with |
|---|---|
| Every predecessor feature `[DONE]` | `PREDECESSOR:F-####` |
| No open blocker on the feature | `BLOCKED` |
| Features in Build (`[SCHEDULED]`, `[IN_BUILD]`, `[INTEGRATING]`) below `MAX_BUILD_WIP` | `WIP` |
| Write set does not overlap a feature in Build (policy `strict`) | `WRITE_SET_CONFLICT:F-####` |
| Constitution version at approval is current, or re-analysis passed | `REANALYZE` |

The first Plan meeting every condition is released: `PlanScheduled`, branch
`feat/F-####-slug` created from the trunk, the approved bundle rendered and
committed onto it, tasks with no predecessors → `[READY]` (each enqueuing its
turn). Evaluation continues down the list while WIP allows. Held Plans record
`PlanHeld` with the reason, visible in the backlog.

Ties on priority are broken by key (older first).

---

## Delivery Lead overrides

| Decision | Effect |
|---|---|
| Reorder | sets a scheduling rank above priority for one feature |
| Force | releases a feature held by `WIP` or an `advisory` write-set conflict; never past `PREDECESSOR`, `BLOCKED`, or `REANALYZE` |
| Hold | keeps a feature out of Build until released |

Every override is a recorded decision on the feature stream.
