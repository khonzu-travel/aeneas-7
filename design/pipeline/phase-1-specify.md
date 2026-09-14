# Pipeline — Phase 1: Specify

**Purpose**: turn intent into an approved Feature Spec.
**Roles**: `analyst`; the Product Owner answers and approves.
**Input**: intent captured in the UI.
**Output**: `spec.md` at `[APPROVED]`.

---

## Flow

1. The Product Owner submits intent in the UI: a description, a priority, a
   type, the measurable constraints the form asks for, and a budget (defaulted
   from the project). If features in flight are below `MAX_OPEN_FEATURES`, the
   platform records `FeatureCreated`, issues `F-####`, and enqueues
   `spec.author`. Otherwise the intent is queued as `PENDING_INTAKE` with its
   position shown to the Product Owner, and admitted when a feature closes —
   backpressure at the front door rather than a burst of authoring turns
   competing for the same workers, models, and reviewers.
2. An analyst turn runs the `specify` skill against the intent, the Charter,
   and the Constitution, and submits `spec.md`. The format verifier refuses a
   version missing a required section.
3. The same turn runs the `clarify` skill over the draft. If it finds
   ambiguity that would change a requirement, it opens a session with at most
   five questions for the Product Owner (`ClarificationOpened`) and ends the
   turn; the spec reports `waiting_on: product_owner`.
4. The Product Owner answers in the UI (`ClarificationAnswered`); the platform
   enqueues `spec.clarify-apply`. The analyst applies the answers into the
   spec and `## Clarifications`, submits a version, and either opens another
   session (up to `MAX_CLARIFY_SESSIONS`) or proceeds.
5. The analyst submits for review. The platform refuses while any
   `[NEEDS CLARIFICATION]` remains or a session is answered and unapplied;
   otherwise `SpecSubmittedForReview` and the Product Owner's inbox gains
   the decision.
6. The Product Owner approves (`SpecApproved`, version pinned, `plan.author`
   enqueued) or rejects with reasons (`SpecRejected`, `rejection_count` up,
   `spec.author` enqueued with the reasons).
7. At `MAX_SPEC_REJECTIONS` the feature is held with `waiting_on:
   product_owner` and a choice: revise the intent (restarts the count) or
   abandon.

---

## What the analyst owes

- A `BUSINESS` spec in business language with no mechanism; a `TECHNICAL`
  spec with a clear objective and no prescribed solution. Either states
  every constraint given at intake as an acceptance criterion.
- User stories ordered P1..Pn, each independently testable, each with
  Given/When/Then scenarios that a tester can turn into tests without
  interpretation.
- `FR-###` for behavior, `SC-###` for measurable outcomes, Key Entities
  without schema, Assumptions for every default taken, Dependencies naming
  predecessor features.

---

## Constraints

- No feature is created before the Constitution is `[APPROVED]`.
- The analyst is the only writer of `spec.md`; the Product Owner changes it
  only by answering or rejecting.
- The Product Owner's approval pins the version every downstream reader of
  authorized content uses.
