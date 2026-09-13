# Workflows — Main Workflow

The happy path from intent to a live, monitored change, with the turns and
decisions it costs.

| Step | Actor | Turn / decision | Events |
|---|---|---|---|
| 1 | Product Owner | submits intent in the UI | `FeatureCreated` |
| 2 | analyst turn | `specify` + `clarify`; opens a session if needed | `SpecVersionSubmitted`, `ClarificationOpened` |
| 3 | Product Owner | answers the session | `ClarificationAnswered` |
| 4 | analyst turn | applies answers; submits for review | `SpecVersionSubmitted`, `ClarificationApplied`, `SpecSubmittedForReview` |
| 5 | Product Owner | approves | `SpecApproved` |
| 6 | planner turn | `plan` + companions + `tasks`; submits the bundle | `PlanVersionSubmitted`, `PlanSubmittedForReview` |
| 7 | analyzer turn | consistency pass | `PlanAnalyzed` |
| 8 | reviewer turns × 3–4, parallel | verdicts | `ReviewStageOpened(agent)`, `ReviewRecorded` × n |
| 9 | Solution Architect | approves | `ReviewStageOpened(human)`, `ReviewRecorded`, `PlanApproved`, `TasksCreated` |
| 10 | scheduler | releases; branch created | `PlanScheduled`, `TaskReady` × k |
| 11 | tester / implementer turns | per task; verifiers run per task | `TaskClaimed`, `TaskImplementationComplete`, `VerifierRunRecorded`, `TaskCompleted`, `PathsFrozen` |
| 12 | merge queue + integrator turn | rebase, full suite, risk | `IntegrationStarted`, `RiskAssessed`, (`RiskAccepted`), `DataModelTranscribed`, `IntegrationSucceeded` |
| 13 | integrator turn | deploy | `DeploymentStarted`, `DeploymentCompleted`, `FeatureCompleted` |
| 14 | operator turns | observe | `AnomalyRecorded` as needed |

Human decisions on the happy path: three (spec, plan, and, for `MEDIUM`/`HIGH`
risk, integration). Model turns before Build: five to seven.

---

## Review model

A review stage opens with `ReviewStageOpened` naming its reviewers; each
records one decision; the stage closes only when all have decided, so a
rejection carries every reviewer's findings. A new version during an open
stage invalidates it (`ReviewsInvalidated`) and reopens the agent stage. A
decision on a closed stage is refused. Human stages open only after agent
stages pass.

| Artifact | Agent stage | Human stage |
|---|---|---|
| Charter | — | Product Owner |
| Constitution | — | Solution Architect, Enterprise Architect |
| Feature Spec | format verifier only | Product Owner |
| Plan | analyzer; architecture, data, security, (UX) reviewers | Solution Architect |
| Amendment | — | Solution Architect, Enterprise Architect |
| Independent Data Model change | data, architecture, (security) reviewers | Solution Architect for `BREAKING` |
| Integration | full verifier run | Solution Architect for `MEDIUM`/`HIGH` |
