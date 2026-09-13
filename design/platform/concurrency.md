# Platform — Concurrency

How many features can be in flight at once, and where they meet. The design
goal is that features contend only where they truly share something, and that
each such place has one explicit rule.

---

## Isolation by stream

Every governed write names one stream. Feature streams are independent:
optimistic concurrency on `(stream_id, stream_seq)` means writers to different
features never wait on each other and never retry because of each other. The
database-level contention v6 had — advisory locks per artifact, projections
updated under those locks, expression-indexed scans of one global table — is
gone by construction. See [`event-store.md`](event-store.md).

**Cross-stream effects are turns, not writes.** An Amendment that affects
twenty open Plans writes one event on the constitution stream and enqueues
twenty `plan.analyze` turns; each turn later writes to its own feature stream.
A `BREAKING` Data Model change resolves its impact list from
`plan_entity_refs` and raises Defects the same way. No transaction ever
spans two streams.

---

## Where features actually meet

| Shared thing | Conflict | Rule | Enforced at |
|---|---|---|---|
| Data Model names | Two features introduce `Subscription` | Reservation to the first Plan past submit-for-review; the second is refused naming the holder | Plan submit |
| Data Model shape | A feature revises an entity another live Plan cites | `change_kind` computed; `BREAKING` refused at submit and at integration; goes through the independent review with the impact list | Plan submit, integration |
| The Constitution | An Amendment changes what open Plans relied on | Re-analyze turns for affected Plans; `CRITICAL` returns them | Amendment applied |
| The codebase | Two features change the same files | Write sets, branches, and the merge queue (below) | Scheduling, verification, integration |
| Human attention | Too many decisions owed | `MAX_BUILD_WIP` and per-role queue caps; inbox ordered by urgency | Scheduling, enqueue |
| Workers | More turns than capacity | Queue depth is the metric; add workers | — |

---

## Write sets

Every Plan declares in `plan.md`:

```markdown
## Write Set
- src/billing/**
- src/api/routes/subscriptions.py
- migrations/2026_09_*.sql
```

The platform normalizes the globs and stores them on the Plan. Two uses:

- **Scheduling.** The scheduler computes overlap between a candidate Plan's
  write set and every Plan in Build. Under policy `strict` (default) an
  overlapping candidate is held with `WRITE_SET_CONFLICT:F-0031` until the
  other integrates; under `advisory` it is scheduled after the other in
  priority order and the conflict is left to the merge queue. Foundational
  paths a project marks `shared` (a router registry, a migration index) are
  excluded from overlap and left to rebase.
- **Verification.** An implementer diff outside the write set fails the
  `write-set` check unless the task's line in `tasks.md` names the path. A
  Plan that needs a wider set is revised, which is a visible decision rather
  than a silent expansion.

---

## Branches and the working tree

At scheduling the platform creates `feat/F-####-slug` from the trunk head and
commits the rendered, approved bundle under `specs/F-####-slug/`. Every
implementer and tester turn works on that branch; the commit its
implementation-complete names is what the verifier runs. Tasks marked `[P]`
may run concurrently on the same branch because they name different files;
a collision surfaces as a verifier failure on the second to complete, and the
returned turn rebases and retries.

The trunk is never written by a worker. Only the merge queue advances it.

---

## The merge queue

A feature whose tasks are all `[DONE]` enters `[INTEGRATING]`. The queue is
ordered by feature priority, then by entry time, and processes one feature per
repository at a time under a repository advisory lock — the single point of
serialization in the system, placed where serialization is unavoidable and
cheap.

```
take head feature F
IntegrationStarted(attempt n, base = trunk head)
enqueue integrate turn:
    rebase feat/F onto trunk (or merge trunk in, per repo policy)
    resolve conflicts within the write set; a conflict outside it is a failure
    push the rebased branch
verifier runner: full suite on the rebased commit (build, lint, types, all
    unit tests, all frozen acceptance and contract tests of F and of the trunk,
    scanners) + risk score
    fail → IntegrationFailed; attempt < MAX_INTEGRATION_ATTEMPTS ? re-enqueue
           : blocker to the Delivery Lead with the report
    pass → RiskAssessed; band LOW → merge; MEDIUM/HIGH → wait for RiskAccepted
platform fast-forwards trunk to the verified commit; DataModelTranscribed;
IntegrationSucceeded; release turn enqueued
release lock; take next
```

A feature waiting on a Solution Architect's risk decision does not hold the
lock: it steps aside, and re-verifies against the new trunk head when the
decision arrives if the trunk moved (a second run is cheap; a stale merge is
not).

Multi-repository projects run one queue per repository; a feature whose write
set spans repositories integrates them in the order its Plan declares, and a
failure in the second rolls the first back by revert.

---

## Work in progress

| Limit | Bounds | Why |
|---|---|---|
| `MAX_BUILD_WIP` | Plans at `[SCHEDULED]`, `[IN_BUILD]`, `[INTEGRATING]` | Reviewer and human attention, merge-queue depth |
| per-role queue cap | `QUEUED` turns per role | Workers per role; keeps claim latency bounded and visible |
| `FEATURE_BUDGET` | spend per feature | The loop's stop |

Held features are visible in the backlog with the reason and the feature
that holds them.

---

## Capacity model

Throughput is bounded by the slowest of: worker capacity per role (add
workers), the merge queue's serial integration time (keep verifier suites
fast; shard by repository), and human decision latency (bounded by WIP, not
by the platform). Nothing in the database is a shared bottleneck between
features except the merge queue's lock and the projectors' single-writer
loops, both of which are off the write path.
