# Workflows — Clarification

A role that cannot proceed without an answer it does not own opens a bounded
session. See [`../ledger/clarification.md`](../ledger/clarification.md) for the
artifact.

```
asker's turn: runs the clarify skill → up to 5 questions with options and a recommendation
   POST /v1/clarifications { artifact, version, target, questions[] }
   ClarificationOpened; artifact reports waiting_on: <target>; turn ends
target (human, in the UI; or a role, as a turn):
   answers each question (or "let the asker decide" for a role target)
   ClarificationAnswered → platform enqueues <asker>.clarify-apply
asker's turn: writes answers into ## Clarifications and the sections they resolve,
   submits a new version, POST /v1/clarifications/{id}/apply { version_id }
   ClarificationApplied; waiting_on clears
```

| Rule | Enforcement |
|---|---|
| ≤ `MAX_CLARIFY_QUESTIONS` per session | refused at open |
| ≤ `MAX_CLARIFY_SESSIONS` per artifact lineage; ≤ `MAX_REVIEW_QUESTIONS` per reviewer per Plan version | refused at open; the asker records assumptions instead |
| No submit-for-review with an answered, unapplied session | refused |
| No status change | `waiting_on` is derived |
| A session outlives nothing | abandonment cancels it |

**Escalation chain.** A planner's question the analyst cannot answer from the
approved spec causes the analyst to open its own session with the Product
Owner; the answer flows back as a spec revision. If the revision changes a
requirement, the spec re-enters the Product Owner's approval and the Plan
waits; if it only clarifies, the spec version is re-pinned without a new
approval and the planner's `clarify-apply` proceeds.
