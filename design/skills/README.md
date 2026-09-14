# Skills

A skill is what a worker loads to execute a turn of a given kind. Skills are
versioned repository content; the platform records `skill@version` on every
turn, so every artifact's audit trail names the instructions that produced it.

---

## Skill contract

```
skills/<name>/
  SKILL.md          front matter + instructions
  templates/        artifact templates the skill fills
  checklists/       rubric answered item by item (reviewer skills)
```

Front matter:

```yaml
name: plan
version: 1.4.0
role: planner
kinds: [plan.author, plan.revise]
model_tier: reasoning
needs_fs: true
inputs:  [spec@approved, constitution@current, data-model, plan@previous?, analyze-report?, verdicts[]?]
outputs: [plan-bundle]
commits: submit-plan                 # the turn's single committing write
tools:   [read-artifact, submit-plan-version, submit-plan, open-clarification, read-data-model]
expected_seconds: 600                # the platform sets the lease to 3× this
slots: 2                             # worker capacity one turn of this kind occupies
checkpoints: [research, data-model, contracts, threat-model, quickstart, tasks]
output_schemas:                      # validated in-turn, per call, before anything is submitted
  plan.md: schemas/plan.schema.json
  data-model.md: schemas/declaration.schema.json
repair_passes: 2                     # bounded; a non-converging repair fails the turn
budget:  { tokens: 400000, cost_micros: 6000000 }
verifier: [format, capabilities, constitution-check, coverage, data-model, write-set, markers]
```

The platform validates on registration that every `kinds` entry maps to
`role`, that `tools` are within the role's permission set, that `commits`
names exactly one write, and that `verifier` names checks the runner has. A
worker refuses a turn naming a version it does not have.

Four fields exist for reliability under load rather than for quality:

| Field | What it buys |
|---|---|
| `commits` | One committing write per turn, so a turn cannot half-create an artifact |
| `expected_seconds` | A lease sized to the turn, so a long turn is not reaped and a dead short one is not held |
| `checkpoints` | A requeued attempt resumes instead of re-deriving, so a crash costs minutes rather than a whole turn's tokens |
| `output_schemas`, `repair_passes` | A malformed or truncated model output is repaired inside the turn, so it costs one small call instead of a requeue that will truncate again |

Skills built on Spec Kit's command templates say so, so that upstream
template changes can be reviewed against the skill.

---

## Catalog

| Skill | Role | Kinds | Tier | Produces | Built on |
|---|---|---|---|---|---|
| `charter` | analyst | `charter.interview`, `charter.author` | reasoning | `charter.md` through a guided interview with the Product Owner | AENEAS charter template |
| `specify` | analyst | `spec.author` | reasoning | `spec.md` | Spec Kit `specify` |
| `clarify` | analyst, planner, reviewers | `spec.clarify`, `spec.clarify-apply`, `plan.clarify-apply` | standard | a session; then the applied version | Spec Kit `clarify` |
| `constitution` | architect | `constitution.author` | reasoning | `constitution.md` from the approved Charter | Spec Kit `constitution` + AENEAS sections |
| `amend` | architect | `amend.author` | reasoning | `A-####.md` with diff, level, impact | — |
| `plan` | planner | `plan.author`, `plan.revise` | reasoning | the bundle; calls `data-model`, `contracts`, `threat-model`, `quickstart`, `tasks`, `checklist` as sub-skills | Spec Kit `plan` |
| `data-model` | planner (sub-skill) | — | reasoning | `data-model.md` with declarations | Spec Kit plan phase 1 + representation contract |
| `contracts` | planner (sub-skill) | — | standard | `contracts/` | Spec Kit plan phase 1 |
| `threat-model` | planner (sub-skill) | — | reasoning | `threat-model.md` with `controlCoverage` | AENEAS security model |
| `quickstart` | planner (sub-skill) | — | standard | `quickstart.md` with assertions | Spec Kit plan phase 1 |
| `tasks` | planner (sub-skill) | — | reasoning | `tasks.md` | Spec Kit `tasks` |
| `checklist` | planner, reviewers | — | fast | `checklists/*.md` | Spec Kit `checklist` |
| `analyze` | analyzer | `plan.analyze` | fast | analyze report | Spec Kit `analyze` |
| `review-architecture` | reviewer.architecture | `review.architecture` | standard | verdict | checklist |
| `review-data` | reviewer.data | `review.data`, `data-model.propose` | standard | verdict; independent change | checklist |
| `review-security` | reviewer.security | `review.security` | standard | verdict | checklist |
| `review-ux` | reviewer.ux | `review.ux` | standard | verdict | checklist |
| `test` | tester | `task.test` | standard | acceptance and contract tests | Spec Kit `implement` (test phase) |
| `triage` | tester | `task.triage` | fast | Bug or Defect decision with evidence | — |
| `implement` | implementer | `task.implement`, `task.setup`, `task.polish` | reasoning | code and unit tests on the branch | Spec Kit `implement` |
| `implement-frontend` | implementer | `task.implement` (UI paths) | reasoning | UI code | Spec Kit `implement` |
| `implement-data` | implementer | `task.foundation` (migrations) | reasoning | migrations, data access | — |
| `fix` | implementer | `task.fix` | reasoning; escalates on attempt 3 | a fix for the failing check | — |
| `defect` | planner | `defect.resolve` | reasoning | a revised bundle | `plan` |
| `integrate` | integrator | `integrate` | standard | a rebased, pushed branch | — |
| `release` | integrator | `release`, `rollback` | standard | deployment signals | project pipeline |
| `observe` | operator | `observe` | fast | anomaly records | — |

---

## Exemplars

- [`plan/SKILL.md`](plan/SKILL.md) — the planner's skill, in full
- [`review-data/SKILL.md`](review-data/SKILL.md) — a reviewer skill with its checklist
