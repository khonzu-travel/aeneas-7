# Changes from AENEAS 6

This is the decisions record for the seventh design. Each section takes one
of the concerns raised against v6, states the v7 decision, and records why.
The final section is a concept-by-concept disposition table so that a reader
who knows v6 can find where every v6 mechanism went.

The concerns, as raised:

1. The Technical Analyst commissioning other agents took many serialized turns.
2. Twelve dedicated agents may not make sense against a pool of workers with
   skills; the roster failed under load.
3. Story and Spec were free-form prose; Spec Kit's fixed formats would be
   better and align with loop engineering.
4. The single event table and synchronous projections limited concurrency and
   throughput once several features ran in parallel.
5. What else should change.

---

## 1. Commissions are replaced by one authoring turn and one parallel review round

**v6.** The Technical Analyst authored the Spec, but every specialist input —
the data model, the threat model, an architecture note, an interaction model,
a deployment note — was a **Commission**: a request record the specialist
started, authored against, delivered, and the Technical Analyst then read,
incorporated into a new Spec version, and settled. Each Commission was at least
three agent turns plus two notifications, and the Spec could not enter review
until all were settled. A feature that needed data, security, and architecture
input spent roughly a dozen agent turns and several hours of wall-clock
latency before a reviewer read anything. Every one of those turns was also a
fresh model context reconstructing the same Spec.

**v7.** The **planner** role produces the entire **Plan bundle** in one turn:
`plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`,
`threat-model.md`, and `tasks.md`, each authored by the corresponding skill
(the same skills a specialist would have used) inside that turn, with
sub-agents where the skill wants them. Specialist expertise enters as a
**review**, not as authorship: when the bundle is submitted, the platform first
runs the **analyze gate** (a deterministic cross-artifact check plus a
model-run consistency pass) and, if that passes, opens one **parallel review
round** — architecture, data, security, and UX when the feature has UI — each
reviewer returning a structured checklist verdict in a single turn. A verdict
may carry a **proposed patch** (a diff against the bundle) so that the
planner's revision turn applies rather than re-derives. The human Solution
Architect is asked only once the round is clean.

| | v6 (data + security + architecture input) | v7 |
|---|---|---|
| Authoring turns before review | Spec draft; 3 × (start, author, deliver); 3 × incorporate; submit ≈ 13 | Plan bundle: 1 |
| Serialized hops | ≈ 8 | 2 (author → review round) |
| Review turns | 3–4, each able to pause the Spec with questions | 3–4 in parallel, one verdict each, questions bounded per round |
| Machine gates before a human sees it | Commission settlement, data-model gates | Analyze gate (coverage, constitution, ambiguity, consistency) plus the data-model gates |

These are design counts, not measurements.

**What is kept from the Commission model.** The property that mattered was
never *who typed the data model*; it was that the design the platform acts on
is **machine-readable where it is approved**. That survives intact:
`data-model.md` carries the same structured declarations, validated against
the Constitution's representation contract at submit, classified by the
platform (a `BREAKING` change is still refused at the gate), reserved by name
across features, and transcribed into the project Data Model **by the
platform** at integration — see §5. The specialist that would have authored
it now reviews it with the same skill, in an independent context, and can
reject or patch it. Author-reviewer separation is enforced structurally: a
review turn is always a fresh turn with no access to the authoring turn's
context (see [`platform/turn-queue.md`](platform/turn-queue.md)).

**What is dropped.** The Commission tables, its eight statuses, its two
counters, the settlement gate, incorporation records, withdrawal cascades, the
Commission read carve-out, and the `DATA_MODEL_UPDATE` task. Data Model
Provenance is restated as "every declaration was reviewed by the data reviewer
role before approval", which the sign-off record already proves.

---

## 2. A worker pool executing role skills replaces the twelve agents

**v6.** Each role was one long-lived process behind a webhook: the platform
POSTed a notification, the agent's handler ran the turn, and the agent kept
its own in-flight guards, retry backoff, reconciliation sweeps, and a latched
model client. Twelve of these ran in one host. Under load, a burst of features
serialized behind whichever role was on the critical path, the sweeps
re-entered flows that were already running, and adding capacity meant adding
another copy of a stateful process that would then race the first one.

**v7.** The platform owns a **turn queue**. Whenever an event calls for work by
a role, the Custodian enqueues a **turn** in the same transaction as the event.
A **worker** is a stateless runtime that claims a turn it is able to run
(`FOR UPDATE SKIP LOCKED`, lease, heartbeat), receives a **per-turn token**
scoped to that turn's role, feature, and artifact, loads the named **skill**,
executes, and completes or fails the turn. Any worker can run any role for
which it has the skill loaded and the model configured. Capacity is the number
of workers; nothing else changes when it grows.

A **role** is therefore two things: a permission set the Custodian enforces on
every write made with the turn's token, and a skill bundle the worker loads.
It is not a process, not a name, and not a conversation. The v6 principle
"Guild roles are teams, not individuals" becomes literal.

**Does separation of roles still matter?** Yes, for one reason only:
separation of duties. The party that authors must not be the party that
verifies, and the party that implements must not be the party that writes the
acceptance tests. Those are properties of *turns* — a review turn is issued
fresh, with its own context, under a role the authoring turn's token could not
have used — and stateless workers give them for free. Everything else that
made roles distinct in v6 (a codename, a webhook, a sweep, a latched client)
was runtime accident.

**Which v6 roles survive as skills.** The analyst (specify, clarify), the
planner (plan, tasks), four reviewers (architecture, data, security, UX), the
implementer (backend and frontend skill variants), the tester, the integrator
(integrate, release), the operator (observe, triage). The Scrum Master's
scheduling and blocker routing become deterministic platform logic with a
human override (§5). The System Architect's `AGGREGATE_DELTA` is gone with
`changeDelta` (§5). The Business Analyst's charter interview is the analyst's
`charter` skill.

**Load behavior.** The queue is the backpressure surface: depth per role is
the load metric, WIP limits per phase bound what enters it, and a turn that
cannot be claimed within its deadline is a visible, alertable condition rather
than a silent stall inside an agent process. Model outages latch a **skill
configuration**, not a worker, so one bad model id stands down one skill's
turns while every other role keeps running. See
[`platform/turn-queue.md`](platform/turn-queue.md).

---

## 3. Artifacts take Spec Kit's formats

**v6.** The Story and the Spec were governed as to ownership, status, and
citations, but their *content* was prose against a section list. Reviewers
argued about proportionality, the platform could check capability identifiers
and entity citations and nothing else, and "is this Spec complete" was a
judgment call every time.

**v7.** The three delivery artifacts and the project constitution adopt
[Spec Kit](https://github.com/github/spec-kit)'s formats, with AENEAS's
governance layered on top rather than replacing them:

| v6 artifact | v7 artifact | Format | Owner role | Approver |
|---|---|---|---|---|
| Archetype | **Constitution** | `constitution.md`: numbered Articles carrying `MUST`/`SHOULD` principles, plus the AENEAS sections the platform reads (capability map, data design language, security model) | architect | Solution Architect + Enterprise Architect |
| Story | **Feature Spec** | `spec.md`: prioritized user stories (P1/P2/P3) with independent-test notes and Given/When/Then scenarios, `FR-###`, `SC-###`, Key Entities, Assumptions, `[NEEDS CLARIFICATION]` markers, a `## Clarifications` session log | analyst | Product Owner |
| Spec | **Plan** (bundle) | `plan.md` (technical context, constitution check, project structure, write set, complexity tracking) with `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `threat-model.md`, `checklists/` | planner | reviewers, then Solution Architect |
| Tasks | **Tasks** | `tasks.md`: `T###`, `[P]` parallel marker, `[US#]` story label, phases (Setup, Foundational, per-story, Polish), exact file paths, checkpoints | planner | approved with the Plan |

Why this is more than a template choice:

- **The format is a verifier.** Because the sections are fixed and the
  identifiers are numbered, the platform's analyze gate can compute coverage
  (every `FR-###` mapped to at least one `T###`, every user story to at least
  one acceptance scenario and one task), detect unresolved
  `[NEEDS CLARIFICATION]` markers, and flag constitution `MUST` violations as
  `CRITICAL` before any reviewer or human spends a turn. Prose cannot be
  checked; a form can.
- **Clarification is a bounded session, not a status.** The `clarify` skill
  scans the nine-category ambiguity taxonomy, asks at most five questions per
  session as multiple choice or short answer, and writes the answers back into
  the spec's `## Clarifications` section and the sections they resolve. A
  human answers a form, not a thread. The `[CLARIFY]` and `[UPDATED]` statuses
  disappear; a feature at `[DRAFT]` with an open session simply reports
  `waiting_on`.
- **Independent slices.** Spec Kit's rule that each user story is an
  independently testable increment gives AENEAS a unit smaller than the
  feature to verify, ship, and roll back, and a natural parallelism unit for
  implementer turns (`[P]` tasks in different files).
- **Coding agents already understand it.** The bundle is rendered onto the
  feature branch under `specs/F-0042-slug/`, so any Spec Kit-aware tool, and
  any implementer skill, reads it as files in the working tree. The content
  store stays the source of truth; the working tree is a projection of it.
- **Loop engineering alignment.** In a loop the verifier is the bottleneck,
  not the generator. Fixed formats with numbered, testable statements are what
  make verifiers writable: `SC-###` become checks, Given/When/Then scenarios
  become acceptance tests, `contracts/` become contract tests, `checklists/`
  become review rubrics.

The full formats are in [`ledger/`](ledger/).

---

## 4. Event streams, asynchronous projections, and write-set scheduling

**v6.** One `events` table with all references inside a JSONB payload, one
per-artifact advisory lock per write, and every projection updated inside the
write transaction (Custodian step 7). Correct, and adequate for one feature at
a time. Under parallel features the costs compounded: every write paid for
every projection it touched; the ready board rewrote every row of a feature on
each task event; expression indexes over payload keys were the only way to
find anything; and the outbox, the sweeps, and the reaper all polled the same
tables. Beyond the database, parallel features collided where no lock existed
at all: in the codebase.

**v7.** Four changes, each removing one class of contention.

**Per-aggregate streams with optimistic concurrency.** Every event belongs to
a stream: a Feature, the Constitution, the Data Model, or the platform stream.
`events(stream_id, stream_seq)` is unique; a writer reads the stream head,
validates, and inserts at `head + 1`. Two writers to the same feature conflict
on the unique index and one retries; writers to different features never touch
the same rows and never wait. There are no advisory locks. Typed columns
(`stream_type`, `stream_id`, `feature_id`, `turn_id`) replace payload
expression indexes. The table is range-partitioned on the global sequence so
that growth is an archival concern rather than an index-depth one. See
[`platform/event-store.md`](platform/event-store.md).

**Gates read aggregate state; projections are read models only.** Entity
tables carry `current_status` and the columns a gate needs, written in the
stream's own transaction — so the gate that decides "may this plan be
scheduled" reads a consistent, current row. Projections (queues, boards,
dashboards) are built **asynchronously** by projectors that read the global
sequence forward from a durable checkpoint. They are never in the write path
and never consulted for a governing decision. Rebuilding is resetting a
checkpoint. A caller that needs read-your-writes passes the sequence its write
returned, and the read waits for the projector to pass it. See
[`platform/projections.md`](platform/projections.md).

**A turn queue instead of a notification fan-out.** Enqueuing a turn is one
row in the same transaction as the event. There is no outbox, no per-agent
webhook, no delivery retry ladder, and no roster-wide sweep inferring lost
notifications from board state. What replaces the sweep is the queue's own
lease: a claimed turn whose lease lapses is requeued. Humans are still
notified (the UI), through a projection.

**Write-set-aware scheduling and a merge queue.** The one shared resource v6
never governed is the code. Every Plan declares its **write set** (paths and
modules it will change) in `plan.md`. The scheduler holds a feature whose
write set overlaps one already in Build (configurable as a hard hold or as an
ordering hint). Each feature builds on its own branch; the **integrator**
rebases onto the trunk, runs the whole verifier suite, and merges, one feature
at a time. The merge queue is the single serialization point in the system,
and it is the one place serialization is cheap. Data Model names are reserved
across features exactly as in v6; the Constitution is amended rarely and an
Amendment triggers a re-analyze turn on every open Plan. See
[`platform/concurrency.md`](platform/concurrency.md).

---

## 5. Further changes

**Platform-run verifiers replace `changeDelta`.** v6 had each Guild Lead score
its own work on a Fibonacci rubric, then a System Architect task RSS-combined
four scores into a band. Self-assessed risk is not governance, and it cost a
scanning state machine, a re-claim, and an extra task per feature. v7 computes
a **risk score** from deterministic signals the platform already holds — diff
size, modules touched, contract surface changed, data-model `change_kind`,
new dependencies, scanner findings, acceptance test delta — and maps it to a
band that decides whether a human reviews the integration. Tests, contracts,
build, lint, and scans run as **verifiers** in a sandbox on every
implementation-complete signal; a failing verifier returns the task, and a
worker cannot override it. See [`platform/verification.md`](platform/verification.md).

**Scheduling is platform logic.** The Scrum Master's ordering rules were
deterministic (priority, predecessors, blockers, WIP) and are now computed by
the platform, with write-set conflicts added. A human **Delivery Lead**
role may reorder or force. Blockers are triaged by rule (machine-resolvable →
cleared; otherwise → the human role that owns the blocked artifact's phase), so
no model turn sits between a blocker and the person who can clear it.

**The analyze gate.** Before any review turn is enqueued, the platform runs
Spec Kit's analyze pass over the bundle: duplication, ambiguity,
underspecification, constitution alignment, coverage gaps, inconsistency.
`CRITICAL` findings return the bundle to the planner without spending a
reviewer or a human. This is where most of v6's review-round rejections are
caught for free.

**The Data Model is transcribed by the platform.** A Plan's `data-model.md`
declarations are approved with the Plan and written into the project Data
Model by the platform when the feature integrates. No task, no turn, no agent.
The v6 reasons for writing in Build (no residue from unbuilt features, the
write is a comparison against the approved declaration) hold better when the
platform does the comparison itself.

**Blocked is a condition, not a status.** v6 threaded `[BLOCKED]` through
every artifact's status table. v7 keeps blockers in a registry and derives a
`blocked` flag; an artifact's status says where it is in its lifecycle, and the
registry says whether it can move. Fewer transitions, no resume edge cases.

**Petition and Amendment collapse into Amendment.** One artifact, one
lifecycle: proposed → under review → approved → applied. The proposal and the
change record were two views of one decision.

**Budgets are a governed bound.** Each feature carries a token and cost budget;
every turn reports usage; exhaustion raises a blocker to the Product Owner.
This is the loop-engineering "stop" for the whole feature loop. Telemetry
beyond the bound stays non-governing.

**Per-skill model routing.** A skill declares a model tier (`reasoning`,
`standard`, `fast`); deployment maps tiers to models. Review checklists and
triage run on fast models; planning and implementation on reasoning models.

**Fewer statuses, fewer humans-in-the-loop, same authority.** Humans approve
the Feature Spec (Product Owner), the Plan (Solution Architect), the
Constitution and its Amendments (Solution Architect and Enterprise Architect),
and high-risk integrations (Solution Architect). Everything else is a machine
gate.

---

## Disposition table

| v6 concept | v7 disposition |
|---|---|
| Charter, charter interview | Kept; the analyst's `charter` skill seeds `constitution.md` |
| Archetype (12 subtypes, `archetype_meta`) | **Constitution**: one document with numbered Articles and the platform-read sections; versioned whole |
| Story | **Feature Spec** (`spec.md`) |
| Spec | **Plan bundle** |
| Task types `DATA_MODEL_UPDATE`, `IMPLEMENTATION`, `TEST_CREATION`, `TEST_EXECUTION`, `AGGREGATE_DELTA` | `tasks.md` entries of kind `setup`, `foundation`, `test`, `implement`, `polish`; the platform runs execution and verification; no aggregate task |
| `BUG`, `DEFECT` tasks | Kept, raised by the platform on verifier failure after a tester **triage** turn decides target (implementer or planner) |
| Commission (all types) | Removed; planner skills author, reviewer skills review in parallel |
| Clarification (dialogue artifact, `@`-mentions, `[CLARIFY]`) | **Clarification session**: bounded structured questions written back into the artifact; no status |
| Petition + Amendment | **Amendment** |
| Data Model (ledger artifact, declarations, classification, reservation, citation) | Kept; written by the platform at integration; declarations authored in `data-model.md` |
| Twelve named agents, agent host, webhooks, sweeps | **Worker pool**, **turn queue**, per-turn tokens, role skills |
| Scrum Master | Platform scheduler + human Delivery Lead override |
| Guild Lead / sub-agent model | A skill may spawn sub-agents inside its turn; the platform sees the turn |
| `changeDelta`, RSS, bands, `AGGREGATE_DELTA` | Platform **risk score** from deterministic signals; band decides human review at integration |
| Scanning states (`SCANNING_*`, `VERIFICATION_FAILED`) | **Verifier run** with two task outcomes: `DONE` or `VERIFICATION_FAILED` |
| Deliverable verification Tier 1 / Tier 2 | Verifier suite: platform checks plus `checklists/` and `quickstart.md` assertions |
| Story Firewall | Removed: implementers read the Feature Spec's scenarios because the tests derive from them. Replaced by **Test Independence**: acceptance tests are authored from spec and contracts before implementation and frozen; an implementer diff touching them fails verification |
| Spec Fidelity, QA Independence, Approved Before Build | Kept in turn-token scope: a turn may read and write only its feature's artifacts, in the statuses its role permits |
| Archetype Supremacy (capability identifiers) | Kept as **Constitution Supremacy**, enforced by the analyze gate and the capability check at submit |
| Sign-off workflow, staged agent-then-human | Kept; agent stage is one parallel review round; invalidation on new version kept |
| `MAX_REJECTION_COUNT`, `MAX_REVIEW_QUESTION_ROUNDS`, `MAX_COMMISSION_*`, `MAX_BUG_RECURRENCE_COUNT` | Restated as declared **loop bounds** in `governance.md`; commission bounds dropped |
| Backlog, ready board, sign-off tracker, blockers, scanning failures projections | Backlog and board become **queue projections** for humans; the turn queue is a table; blockers registry kept; scanning failures folded into verifier-run failures |
| Notification outbox, drain | Removed; turn queue rows are the obligation |
| Active claims, stale-claim reaper, heartbeat | Turn leases and heartbeats; the reaper requeues turns |
| Idempotency keys | Kept |
| Execution provenance, turn telemetry, model price, efficiency report | Kept, simplified: every turn records usage; **budgets** are governed; the rest is non-governing |
| Abandonment | Kept; cascades along the feature stream |
| Operations anomaly, escalation routing, security escalation | Operator skill records anomalies; routing is by rule to the owning human; a fix is a new feature |
| Greek codenames | Dropped; skills are named by what they do |
