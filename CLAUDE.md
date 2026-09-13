# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this repository is

The **design specification for AENEAS 7**, a governed, loop-driven software
delivery platform operated by a pool of workers executing role skills. It is
Markdown only. There is no code here; an implementation conforms to this design
and never the other way around.

Start with `README.md` (what changed since v6 and why), then `design/overview.md`.
`design/changes-from-v6.md` is the decisions record: when a question is "why
does v7 do X", the answer is there or belongs there.

## Core model

- **The platform owns all state.** Workers submit content and signal actions
  through the `/v1` API with a per-turn token; they never write status.
- **Work is turns, not notifications.** The platform enqueues a turn when an
  event calls for one; any worker holding the role's skills claims it. There
  are no long-lived per-role agents and no webhooks to agents.
- **Loops are declared.** Every generate → verify → retry cycle names its
  verifier, its bound, and its stop condition. A bound the platform does not
  count is not a bound.
- **Artifacts have fixed formats**, taken from Spec Kit: `spec.md` (Feature
  Spec), the `plan.md` bundle (Plan), `tasks.md` (Tasks), `constitution.md`.
  Free-form prose is refused where a section is required.
- **One stream per feature.** Events for a feature are an ordered stream with
  optimistic concurrency; projections are asynchronous and checkpointed; gates
  read aggregate state, never a projection.
- **Verifiers, not self-assessment.** The platform runs tests, contracts,
  scans and the analyze gate; risk is computed from deterministic signals.

## Document map

| Topic | File |
|---|---|
| The system in one page | `design/overview.md` |
| Decisions and their v6 antecedents | `design/changes-from-v6.md` |
| Roles, skills, worker pool, human roles | `design/roles.md` |
| Governance rules, invariants, loop bounds | `design/governance.md` |
| Constitution (replaces Archetype) | `design/ledger/constitution.md` |
| Feature Spec (`spec.md`) | `design/ledger/feature-spec.md` |
| Plan bundle (`plan.md` and companions) | `design/ledger/plan.md` |
| Tasks (`tasks.md`) and task lifecycle | `design/ledger/tasks.md` |
| Project Data Model | `design/ledger/data-model.md` |
| Clarification sessions | `design/ledger/clarification.md` |
| Amendments to the Constitution | `design/ledger/amendment.md` |
| Phases as loops | `design/pipeline/overview.md` and `phase-*.md` |
| Turn queue and worker contract | `design/platform/turn-queue.md` |
| Event store (streams, OCC, partitioning) | `design/platform/event-store.md` |
| Projections (async, checkpointed) | `design/platform/projections.md` |
| Concurrency: streams, write sets, merge queue | `design/platform/concurrency.md` |
| Verification and risk scoring | `design/platform/verification.md` |
| Database schema | `design/platform/database-schema.md` |
| Recovery | `design/platform/recovery.md` |
| End-to-end and alternate flows | `design/workflows/` |
| Skill catalog and exemplar | `design/skills/` |
| Build epics | `roadmap.md` |

## Writing style

- Present tense, declarative: "The platform refuses…", "A worker may not…".
- Tables for permissions, statuses, events, bounds.
- Every state transition names its trigger and its resulting status.
- Distinguish **structural** rules (the platform enforces them) from
  **behavioral** ones (a skill instructs them). Only structural rules count as
  governance.
- When a change touches behavior, update the canonical document from the map
  above and, if it reverses a v6 decision, add a row to `changes-from-v6.md`.
