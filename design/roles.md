# Roles, Skills, and the Worker Pool

A **role** is a permission set plus a skill bundle. A **worker** is a stateless
runtime that executes one **turn** at a time as whatever role the turn names.
Nothing in the system is a long-lived agent.

---

## Why roles are not processes

v6 ran one process per role. That made the role's identity, its webhook, its
retry state, its model client, and its reconciliation sweep all the same
object, so the platform could only scale a role by duplicating a stateful
process that then raced its twin. It also meant a role on the critical path
was a single lane.

v7 keeps what a role is *for* — a bounded set of permissions and a bounded set
of competences — and discards the process. The Custodian enforces the
permission set on every write made with a turn token, and the worker enforces
the competence by loading the skill the turn names. Any worker with the skill
installed and the model tier configured can take any turn of that role.
Adding a worker adds capacity to every role at once.

Separation of duties survives at the turn level: the platform never issues a
review turn to the context that authored what is under review, because every
turn is a fresh context. See [`platform/turn-queue.md`](platform/turn-queue.md).

---

## Role catalog

| Role | Skills | Reads | Writes (through the API, within the turn's feature scope) | Model tier |
|---|---|---|---|---|
| `analyst` | `charter`, `specify`, `clarify` | Intent, Charter, Constitution, Feature Spec | Charter content; Feature Spec versions; clarification questions to the Product Owner; submit-for-review | reasoning |
| `planner` | `plan`, `tasks`, `defect` | Feature Spec (approved), Constitution, Data Model, Plan bundle, review verdicts, verifier reports | Plan bundle versions (all files), `tasks.md`, clarification questions to the analyst, submit-for-review, Defect resolutions | reasoning |
| `architect` | `constitution`, `amend` | Charter (approved), Constitution, Amendments, Plans (for impact) | Constitution versions, Amendment proposals and content | reasoning |
| `reviewer.architecture` | `review-architecture` | Plan bundle, Constitution, Data Model | Review verdict with checklist and optional patch; bounded questions | standard |
| `reviewer.data` | `review-data` | Plan bundle, Constitution §Data Design Language, Data Model | Review verdict with checklist and optional patch; bounded questions | standard |
| `reviewer.security` | `review-security` | Plan bundle, Constitution §Security Model, `threat-model.md` | Review verdict with checklist and optional patch; bounded questions | standard |
| `reviewer.ux` | `review-ux` | Plan bundle, Feature Spec scenarios, Constitution §Interface Conventions | Review verdict with checklist and optional patch; bounded questions | standard |
| `tester` | `test`, `triage` | Feature Spec, `contracts/`, `quickstart.md`, `tasks.md` (test tasks); verifier reports | Acceptance and contract test files on the feature branch; Bug/Defect triage decisions | standard |
| `implementer` | `implement`, `implement-frontend`, `implement-data`, `fix` | Plan bundle, `tasks.md`, Feature Spec scenarios, the feature branch, verifier reports | Code, migrations, unit tests on the feature branch; task claim, implementation-complete; blockers | reasoning |
| `integrator` | `integrate`, `release` | The feature branch, the trunk, verifier reports, risk report | Rebase/merge resolution on the feature branch; deployment signals | standard |
| `operator` | `observe`, `triage-anomaly` | Telemetry, deployment records | Anomaly records | fast |
| `analyzer` | `analyze` | Feature Spec, Plan bundle, Constitution | Analyze report | fast |

Model tiers are deployment-mapped names, not model ids. A skill may raise its
tier for a turn kind (a `fix` on a third attempt may escalate to `reasoning`);
it may never lower another role's.

The `analyzer` role exists so that the analyze gate is a turn like any other —
queued, leased, budgeted, and auditable — rather than logic hidden in the
Custodian. Its deterministic passes run in the platform; its consistency pass
is the turn.

---

## What a role may never do

These hold regardless of skill, because the Custodian enforces them on the
turn token:

| Rule | Enforcement |
|---|---|
| Write outside the turn's feature | The token carries `feature_id`; a write naming another feature's artifact is refused |
| Write an artifact its role does not own | The permission set names the artifact types and statuses the role may write |
| Write status | No endpoint accepts a status; every transition is the Custodian's response to a validated signal |
| Act after the turn ends | The token expires at turn completion, failure, or lease lapse |
| Author and review the same version | A review turn is refused for a version whose authoring turn ran under a token from the same worker session; workers are stateless so this only guards a misconfigured deployment |
| Modify frozen acceptance tests | The verifier fails an implementer diff that touches paths frozen at the tester's task completion |
| Exceed the turn budget | The worker reports usage on heartbeat; the platform fails the turn at the budget and records why |

---

## Human roles

Humans act only through the UI, which calls the Custodian on their behalf.
Every human decision is an event.

| Human role | Approves | Decides | Reads |
|---|---|---|---|
| Product Owner | Charter, Feature Spec | Answers clarification sessions; abandons a Feature; releases a budget hold | Everything on their features except the working tree |
| Solution Architect | Plan, Constitution, Amendment | Reviews `MEDIUM`/`HIGH` risk integrations; resolves a recurring-failure escalation | Everything |
| Enterprise Architect | Constitution, Amendment | — | Constitution, Amendments, Charter |
| Delivery Lead | — | Reorders or forces scheduling; clears judgment blockers; retries a failed turn; abandons a task | Queues, board, blockers, turns, budgets |
| Admin | — | Operates the platform: worker registry, skill versions, model tiers, projection rebuilds | Operational surfaces |

There is no human role that authors an artifact. A Product Owner who wants a
different Feature Spec answers a clarification or rejects with a reason; the
analyst revises.

---

## Skills

A skill is a versioned directory:

```
skills/<name>/
  SKILL.md        front matter (name, role, version, model_tier, inputs,
                  outputs, tools, verifier, budget) + the instructions
  templates/      artifact templates the skill fills (Spec Kit templates
                  where one exists)
  checklists/     the rubric a reviewer skill answers, item by item
```

The platform records the skill name and version on every turn, so a change to
a skill is visible in the audit trail of every artifact produced after it.
Skills are repository content, versioned with the design, and the worker
refuses to run a turn naming a skill version it does not have.

The catalog and an exemplar are in [`skills/`](skills/).

---

## The worker

A worker is a process that:

1. Advertises the roles it can run (the skills it has loaded and the model
   tiers it can reach).
2. Claims one turn at a time from the queue for those roles.
3. Receives the turn's token, budget, and artifact references.
4. Materializes the feature's working tree (branch checkout plus the rendered
   `specs/F-####-slug/` bundle) when the skill needs a filesystem.
5. Executes the skill, calling the `/v1` API for every read and write.
6. Heartbeats with usage; completes or fails the turn with a structured result.

A worker holds no state between turns. Two workers are interchangeable; a
worker that dies loses at most the turn it held, which requeues at lease
expiry. See [`platform/turn-queue.md`](platform/turn-queue.md).

Inside a turn, a skill may run sub-agents, parallel tool calls, or a
Spec Kit command. The platform sees the turn's reads, writes, usage, and
result. It never sees the sub-agents, which is the v6 Guild Lead abstraction
kept at the only level it was ever needed.
