# Platform — Recovery

What survives a crash, and how. The mechanisms are fewer than in v6 because
the turn queue replaced notifications, sweeps, and claim projections with one
leased table.

| Failure | What is at risk | Recovery |
|---|---|---|
| Worker dies mid-turn | The model output since its last checkpoint | Lease lapses; the reaper requeues the turn with its attempt count and its checkpoints. The next worker resumes from the last checkpoint rather than re-deriving. The dead worker's token is refused, and its next heartbeat (if it revives) answers `CANCELLED` |
| Worker alive but the artifact moved | Every token the turn spends after that | The heartbeat answers `SUPERSEDED`; the worker stops before its next model call. Its completion would be refused anyway, so the only thing at stake is waste, bounded to one heartbeat interval |
| A model call returns unparseable or malformed output | The turn | The skill's bounded repair pass runs inside the turn against the declared output schema. Only a non-converging repair fails the turn, and it resumes from the last checkpoint |
| Lease lapses because the platform was slow, not because the worker died | Live work reclaimed | Cannot happen by construction: the heartbeat path is a single indexed row update on a reserved connection allowance, and requeuing re-validates under the row lock, so a turn that heartbeated between detection and requeue is left alone |
| A turn is enqueued twice | Two turns authoring one artifact | Cannot happen: a partial unique index allows one live turn per `(stream, kind, artifact)`; the second enqueue is a no-op |
| A turn dies between two writes | A half-created artifact | Cannot happen: a turn has exactly one committing write |
| Platform dies mid-write | Nothing: the transaction rolled back | The caller retries with the same `Idempotency-Key` |
| Platform dies after commit, before the response | A duplicate on retry | `processed_requests` replays the stored result |
| Verifier runner dies mid-run | A run stuck at `RUNNING` | The reaper re-drives runs past their timeout as `INFRA` (not counted as an attempt); suites are deterministic and re-runnable |
| Projector dies | Nothing: the checkpoint advances with the batch | It resumes from the checkpoint; handlers are idempotent |
| Merge queue dies mid-integration | The repository lock, a half-pushed branch | The lock is session-scoped and drops; the next pass finds the `[INTEGRATING]` feature with `IntegrationStarted` and no outcome, re-enqueues the `integrate` turn, which rebases again from the recorded base or the new trunk head |
| Model endpoint refuses the configuration | Every turn of that skill | `skill_standdowns` holds the skill's turns visibly; an Admin fix plus clear resumes them at once |
| Model refuses one request | That turn | `FAILED` non-retryable; the feature shows `waiting_on: delivery_lead`; retry by decision |
| No worker can serve a role | Turns age past `deadline` | The queue reports it as an operator alert on the features it holds |
| The turn queue table is lost | Owed work | Rebuildable: replay the enqueue rules over each stream from the last completed turn per `(stream, kind, artifact)` |

---

## Startup

On boot the platform runs one pass: requeue lapsed turns, re-drive timed-out
verifier runs, resume the merge queue, start projectors from their
checkpoints. Nothing waits for a periodic sweep to notice; the periodic reaper
exists for the same three conditions arising while the platform is up.

---

## Detection is state-based

Every recovery condition is a direct query: `turns WHERE status='CLAIMED' AND
lease_expires_at < now()`, `verifier_runs WHERE status='RUNNING' AND started_at
< now() - timeout`, `plans WHERE current_status='INTEGRATING'` with no live
integrate turn. No consumer cursor over the event store is involved except the
projectors' own.

---

## Idempotency

Every write accepts an `Idempotency-Key`. The Custodian claims the key in the
same transaction as the write; a retry replays the stored result; a concurrent
duplicate blocks on the key row until the first commits, then replays. Workers
generate one key per logical write and retry transient failures with backoff.
