# Platform — Verification

A worker's claim of success never completes anything. The platform runs the
verifier, records the report, and decides. This document defines the verifier
suites, the analyze gate, frozen paths, and the risk score.

---

## Principle

In a loop the verifier is the bottleneck, and the generator's opinion of its
own work is not a verifier. v6 asked each Guild Lead to score its own change
on a rubric and combined the scores into a risk band; v7 replaces
self-assessment with deterministic checks the platform runs in a sandbox and a
risk score computed from signals those checks produce.

---

## Project verifier configuration

A project declares its verifiers once, in the repository:

```yaml
# .aeneas/verify.yml
image: ghcr.io/org/project-ci:2026.09
commands:
  build:        make build
  lint:         make lint
  typecheck:    make typecheck
  unit:         make test-unit
  acceptance:   make test-acceptance ARGS="$PATHS"
  contract:     make test-contract ARGS="$PATHS"
  migration:    make migrate-dry-run
scanners:
  - static_analysis
  - dependency_audit
  - secrets
  - container
timeouts: { default: 900 }
```

The verifier runner executes suites in a fresh container from `image` on the
named commit, with no network except what the project allows, and captures
every command's exit code and output.

---

## Suites by task kind

| Kind | Checks |
|---|---|
| `setup` | build, lint |
| `foundation` | build, lint, typecheck, unit, migration |
| `test` | test files parse and are collected; the story's acceptance and contract tests **fail** against the branch (a test that passes before implementation tests nothing); no production path touched |
| `implement` | build, lint, typecheck, unit, acceptance and contract tests for the task's story (frozen), scanners, write-set check, frozen-path check |
| `polish` | build, lint, typecheck, unit, all frozen tests of the feature |
| `bug` | the check that raised it, then the `implement` suite |
| integration | everything above across the whole feature and the trunk, plus risk assessment |

Every run is recorded as `VerifierRunRecorded` with each check's result and
output. A failing run returns the task with the report as the next turn's
input; nothing overrides it. A run that fails for infrastructure reasons (the
image would not start, a timeout before any check ran) is recorded as
`INFRA` and re-driven by the reaper, not counted as an attempt.

---

## Frozen paths

When a `test` task completes, the platform records `PathsFrozen` for the test
files it produced. From then on, any implementer diff on the feature branch
that changes a frozen path fails the `frozen-path` check. The tester may
revise its own tests only through a new `test` task raised by a Defect
resolution (the Plan changed, so the tests may). This is Test Independence
made structural.

---

## Checklist and quickstart assertions

`quickstart.md` steps and `checklists/` items may be written as machine
assertions:

```markdown
- [ ] `POST /subscriptions` with a valid body returns 201 and a `subscription_id`  {assert: contract:subscriptions#start}
- [ ] Cancelling keeps read access until `current_period_end`               {assert: acceptance:US2-S3}
- [ ] No endpoint returns `card_number`                                       {assert: scan:secrets-in-responses}
```

An assertion names a check the runner can evaluate; an item without one is a
reviewer's item and is answered in the verdict. Coverage at Plan submit
requires every `SC-###` to be reachable by at least one assertion or one
reviewer checklist item.

---

## The analyze gate

Runs when a Plan is submitted, before any reviewer turn.

**Deterministic passes (platform):**

| Pass | Refuses when |
|---|---|
| Format | any bundle file misses a required section or numbering |
| Capabilities | `## Required Capabilities` names an identifier the Constitution does not grant |
| Constitution Check | any Article marked `FAIL`, or an Article missing from the table |
| Coverage | an `FR-###`, user story, or `SC-###` maps to nothing; a `T###` maps to no story or requirement |
| Data Model | a citation of an unknown/deprecated/retired document; a reservation conflict; a `BREAKING` classification; a declaration failing the representation contract |
| Write set | empty, or a path outside the repository |
| Markers | any `NEEDS CLARIFICATION` left in the bundle |

**Consistency pass (an `analyzer` turn):** duplication, ambiguity,
underspecification, constitution-alignment reasoning, cross-artifact
inconsistency (terminology drift, ordering contradictions between `plan.md`
and `tasks.md`). Output is a report table with severity; `CRITICAL` returns
the Plan to the planner; lower severities travel to the reviewers as context.
Reaching `MAX_ANALYZE_RETURNS` holds the Plan for the Solution Architect with
the report rather than re-running the planner again.

---

## Risk score

Computed by the platform at integration from the integration run and the
Plan:

| Signal | Source | Contribution |
|---|---|---|
| Diff size | lines added + deleted, log-scaled | 0–2 |
| Spread | distinct top-level modules touched | 0–2 |
| Surface | contracts added, changed, or removed (`contracts/` diff against trunk) | 0–3; a removed or changed existing contract is ≥ 2 |
| Data | max `change_kind` among declarations (`ADDITIVE` 0, `STRUCTURAL` 2); any `sensitivity` introduced +1 | 0–3 |
| Dependencies | new or upgraded dependencies; any with known advisories | 0–3; any advisory ≥ 2 |
| Findings | scanner findings by severity; `HIGH`/`CRITICAL` are blockers, not signals | 0–2 |
| Tests | ratio of frozen tests to `FR-###`; acceptance tests that changed since freezing (should be 0) | 0–2 |
| History | `bug_count`, verify attempts, integration attempts for the feature | 0–3 |

`score = Σ contributions` (0–20). Bands: `LOW` < 6, `MEDIUM` 6–11, `HIGH` ≥ 12,
project-tunable. `LOW` merges on the verifier's pass alone; `MEDIUM` and
`HIGH` wait for `RiskAccepted` from the Solution Architect, who sees the
signals, the report, and the diff. A Solution Architect review is also
required, regardless of band, when `MAX_BUG_RECURRENCE` was reached.

The score is recorded (`RiskAssessed`) with its signals so that the band a
human accepted is auditable and the weights can be tuned against outcomes.
