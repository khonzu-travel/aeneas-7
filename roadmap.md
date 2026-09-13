# Roadmap

The build backlog for AENEAS 7 at epic granularity. Stories are derived from
these epics, one per file, when implementation begins; each cites the design
documents it implements.

| # | Epic | Scope | Design |
|---|---|---|---|
| 1 | Event streams and Custodian | `events` with streams, OCC write protocol, typed columns, partitioning, append-only triggers, idempotency keys, entity tables with `stream_seq` | `platform/event-store.md`, `platform/database-schema.md` |
| 2 | Turn queue and workers | `turns`, claim protocol, per-turn tokens, leases, heartbeats, reaper, stand-downs, enqueue rules, one-live-turn index, worker registry, a reference worker runtime | `platform/turn-queue.md`, `roles.md` |
| 3 | Projectors | checkpointed projectors on `commit_xid`, read-your-writes, rebuild, the read models in `projections.md`, keyset paging | `platform/projections.md` |
| 4 | Artifact formats and parsers | parsers and format verifiers for `spec.md`, the Plan bundle, `tasks.md`, `constitution.md`, declarations; rendering to Markdown and to the working tree | `ledger/` |
| 5 | Charter and Constitution | onboarding interview, Constitution authoring and two-human review, semver, Amendment lifecycle and cascade | `ledger/constitution.md`, `ledger/amendment.md`, `workflows/amendment.md` |
| 6 | Specify | intent capture, `specify` and `clarify` skills, clarification sessions, Product Owner review, bounds | `pipeline/phase-1-specify.md`, `ledger/feature-spec.md`, `ledger/clarification.md` |
| 7 | Plan | `plan` skill and sub-skills, deterministic gates, `analyze` skill and gate, parallel review round with verdicts and patches, staged human review, invalidation, bounds | `pipeline/phase-2-plan.md`, `ledger/plan.md`, `workflows/review-and-rework.md` |
| 8 | Data Model | project Data Model tables, declarations, classification, reservations, citations, transcription at integration, independent changes | `ledger/data-model.md`, `workflows/data-model-change.md` |
| 9 | Scheduler | gate evaluation, WIP, write-set overlap and policy, branch creation and bundle rendering, Delivery Lead overrides | `pipeline/phase-3-schedule.md`, `platform/concurrency.md` |
| 10 | Build and verification | task records from `tasks.md`, task lifecycle, `test`/`implement`/`fix` skills, sandboxed verifier runner and `.aeneas/verify.yml`, frozen paths, write-set check, triage, Bug/Defect, bounds | `pipeline/phase-4-build.md`, `ledger/tasks.md`, `platform/verification.md` |
| 11 | Merge queue and release | integration turn, full-suite run, risk score and bands, risk acceptance, trunk fast-forward, `release` skill, rollback | `pipeline/phase-5-integrate-release.md`, `platform/concurrency.md` |
| 12 | Blockers, abandonment, recovery | blocker registry and routing rules, abandonment cascades, startup pass, reaper, re-drives | `workflows/blocked.md`, `workflows/abandonment.md`, `platform/recovery.md` |
| 13 | Budgets and telemetry | usage ledger, model prices, feature and turn budgets as bounds, turn metrics, efficiency views | `governance.md`, `platform/projections.md` |
| 14 | Human UI | inboxes, feature dashboard with derived phase and `waiting_on`, decision and answer forms, board, blockers, merge queue view, audit timeline, admin surfaces | `platform/overview.md`, `platform/projections.md` |
| 15 | Operate | anomaly rules, `observe` skill, routing to inboxes, rollback decision path | `pipeline/phase-6-operate.md` |
| 16 | End-to-end harness | a real platform, a real worker pool with stubbed models, a real sandbox runner, the happy path and every bound exercised | `workflows/main-workflow.md` |

Epics 1–4 are the foundation and precede everything else. Epics 5–8 deliver
the pre-Build pipeline and can be exercised end to end with a stub scheduler.
Epics 9–11 deliver Build and integration. Epics 12–16 harden and expose.
