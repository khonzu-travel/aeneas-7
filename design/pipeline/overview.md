# Pipeline — Overview

Six phases, each a declared loop with a gate. Work enters as intent and exits
as an integrated, released, monitored change. No phase is skipped; no gate is
bypassed.

```
 Intent ─▶ [1 Specify] ─▶ [2 Plan] ─▶ [3 Schedule] ─▶ [4 Build] ─▶ [5 Integrate & Release] ─▶ [6 Operate]
              analyst       planner      platform       tester        integrator                 operator
              ↑ PO          reviewers    (Delivery      implementer   merge queue                anomaly →
              approves      ↑ SA         Lead override) verifiers     ↑ SA on MEDIUM/HIGH        new Feature
                            approves
```

| Phase | Loop | Gate out |
|---|---|---|
| 1 Specify | analyst authors `spec.md`; clarify sessions with the Product Owner; format verifier | Feature Spec `[APPROVED]` by the Product Owner |
| 2 Plan | planner authors the bundle; analyze gate; parallel review round; revise | Plan `[APPROVED]`: analyze clean, every reviewer approved, Solution Architect approved |
| 3 Schedule | platform evaluates priority, predecessors, blockers, WIP, write sets | Plan `[SCHEDULED]`; tasks with no predecessors `[READY]` |
| 4 Build | tester and implementer turns per task; sandboxed verifiers; bounded retries; triage | every task `[DONE]`; no open blocker |
| 5 Integrate & Release | merge queue: rebase, full verifier run, risk band, merge, deploy | `DeploymentCompleted` healthy |
| 6 Operate | operator observes; anomalies recorded and routed | an anomaly needing change becomes a new Feature |

---

## The platform in every phase

- Enqueues the turn each event calls for and issues the token it runs under
- Validates every signal against the artifact's state and the role's permissions
- Runs every verifier: format checks, the analyze gate, data-model gates, sandboxed suites, the risk score
- Counts every bound and enqueues the declared escalation when one is reached
- Executes every transition atomically with its event
- Derives each feature's phase, `waiting_on`, and `blocked` for humans

The platform does not judge quality beyond what a verifier can check, does not
direct how a skill works, and does not resolve an ambiguity: it routes it as a
clarification or a blocker.

---

## Gates

| Gate | Condition |
|---|---|
| Specify → Plan | Feature Spec `[APPROVED]` |
| Plan → Schedule | Plan `[APPROVED]` against the current Constitution version |
| Schedule → Build | Plan `[APPROVED]`; predecessors `[DONE]`; no open blocker; WIP below `MAX_BUILD_WIP`; write set clear under policy |
| Build → Integrate | every task `[DONE]` with a passing verifier run; no open blocker; no open Bug or Defect |
| Integrate → Release | rebased branch passes the full suite; risk band `LOW`, or `RiskAccepted` |
| Release → Operate | `DeploymentCompleted` with health checks green |

Detailed phases: [`phase-1-specify.md`](phase-1-specify.md),
[`phase-2-plan.md`](phase-2-plan.md), [`phase-3-schedule.md`](phase-3-schedule.md),
[`phase-4-build.md`](phase-4-build.md), [`phase-5-integrate-release.md`](phase-5-integrate-release.md),
[`phase-6-operate.md`](phase-6-operate.md).
