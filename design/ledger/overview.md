# Ledger — Overview

The Ledger is the set of governed artifacts. Content lives in the platform's
content store as append-only versions; the platform renders each feature's
artifacts into its working tree so skills and tools read them as files.

---

## Artifacts

| Artifact | Scope | File form | Owner role | Stream |
|---|---|---|---|---|
| Charter | project (singleton) | `charter.md` | analyst | constitution |
| Constitution | project (singleton) | `constitution.md` | architect | constitution |
| Amendment | project, many | `amendments/A-####.md` | architect | constitution |
| Data Model | project, one document per entity, enumeration, or the overview | `data-model/<kind>/<name>.md` | platform (transcribed) or `reviewer.data` (independent change) | data_model |
| Feature Spec | feature (one) | `specs/F-####-slug/spec.md` | analyst | feature |
| Plan bundle | feature (one) | `specs/F-####-slug/plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `threat-model.md`, `checklists/` | planner | feature |
| Tasks | feature (one) | `specs/F-####-slug/tasks.md` | planner | feature |
| Clarification session | inside the artifact it clarifies | `## Clarifications` section | the asking role | feature (or constitution) |
| Review verdict | per reviewer per Plan version | `reviews/<role>-v<n>.md` | reviewer roles | feature |
| Verifier report | per task per attempt | platform-generated | platform | feature |

---

## Versioning

Every submission is a new version row. The current version is the newest.
Approval pins a version: `approved_version_id` on the entity is what every
downstream reader of *authorized* content uses, never "the latest".

A bundle (the Plan) versions as a whole: one version row carries every file's
content, so a reviewer approves a consistent set. Individual files are not
versioned separately.

---

## Rendering into the working tree

For each feature the platform maintains a branch `feat/F-####-slug`. At the
start of every turn that needs a filesystem, the worker materializes the
branch and the platform writes the current (or, in Build, the *approved*)
artifact versions under `specs/F-####-slug/`. Those files are read-only to the
skill; a skill produces a new artifact version by submitting through the API,
not by committing the file. The commit that carries the rendered bundle onto
the branch is the platform's, so the branch history records which artifact
version each code commit was built against.

This is what makes Spec Kit-shaped skills, and any Spec Kit-aware tool, work
unchanged: they find `spec.md`, `plan.md`, and `tasks.md` where they expect
them.

---

## Reference keys

| Artifact | Key | Issued |
|---|---|---|
| Feature | `F-####` | at intent capture, from `feat_seq` |
| Feature Spec, Plan, Tasks | borrow the feature's key: `F-0042` spec / plan / tasks | — |
| Task | `T###`, unique within the feature (`F-0042/T017`) | by the platform when `tasks.md` is accepted |
| Amendment | `A-####` | from `amnd_seq` |
| Data Model document | `(kind, name)` | the name is the identifier |
| Turn | UUID | at enqueue |

UUIDs are the identity everywhere in storage and the API; keys are derived on
read and resolved on input.

---

## Status vocabulary

Fewer statuses than v6, because blocked is a condition and clarification is a
session.

| Status | Applies to | Meaning |
|---|---|---|
| `[DRAFT]` | Feature Spec, Plan, Constitution, Amendment | Being authored or revised by the owner role |
| `[ANALYZING]` | Plan | Submitted; the analyze gate is running |
| `[UNDER_REVIEW]` | Feature Spec, Plan, Constitution, Amendment | Reviewers (agent stage, then human stage) hold open decisions |
| `[APPROVED]` | Feature Spec, Plan, Constitution, Amendment | All required decisions recorded as approved; version pinned |
| `[REJECTED]` | Feature Spec, Plan, Constitution, Amendment | The stage closed with a rejection; returned to the owner role with every reason |
| `[SCHEDULED]` | Plan | The scheduler released the feature into Build; tasks may be claimed |
| `[IN_BUILD]` | Plan | The first task was claimed |
| `[INTEGRATING]` | Plan | All tasks `[DONE]`; the feature is in the merge queue |
| `[DONE]` | Feature Spec, Plan, Feature | Integrated and released |
| `[APPLIED]` | Amendment | Its Constitution change is in force |
| `[ABANDONED]` | Feature and everything under it; Amendment | Retired by a human decision. Terminal |

Derived conditions carried on every read, never stored as status: `blocked`
(an open blocker names the artifact), `waiting_on` (the role or human whose
turn or decision is next), `held_by` (the scheduler's reason for holding a
`[APPROVED]` Plan).

Task statuses are in [`tasks.md`](tasks.md).
