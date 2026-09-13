# Ledger — Clarification Session

A clarification is a bounded, structured question-and-answer session that a
role opens against an artifact when it cannot proceed without an answer it
does not own. It is not a status, not a task, and not a free dialogue.

---

## Shape

A session belongs to an artifact version and a target:

| Field | Meaning |
|---|---|
| `artifact` | The Feature Spec, Plan, or Constitution being clarified |
| `asked_by` | The role (or human) asking |
| `target` | The role or human that answers: Product Owner for intent; analyst for spec meaning; planner for plan meaning; Solution Architect for architecture direction |
| `questions[]` | Up to `MAX_CLARIFY_QUESTIONS`, each with a category from the taxonomy, a recommended answer, and either 2–5 options or a short-answer prompt |
| `answers[]` | One per question, recorded as an event when the target answers |
| `applied_version` | The artifact version the asker wrote the answers into |

Rendered into the artifact:

```markdown
## Clarifications
### Session 2026-09-12 (asked by analyst, answered by Product Owner)
- Q: Should a cancelled subscription keep read access until period end? → A: Yes, until period end
- Q: Retention for card_last4 after cancellation? → A: 90 days
```

---

## Taxonomy

The `clarify` skill scans against these categories and asks only where the
answer would change a requirement, a task, or a verifier: functional scope;
domain and data model; interaction and UX flow; non-functional requirements;
integrations and external dependencies; edge cases and failure handling;
constraints and trade-offs; terminology; completion signals.

---

## Rules

| Rule | Enforcement |
|---|---|
| At most `MAX_CLARIFY_QUESTIONS` per session | the platform refuses a sixth |
| At most `MAX_CLARIFY_SESSIONS` per artifact version lineage; at most `MAX_REVIEW_QUESTIONS` per reviewer per Plan version | refused at the limit; the asker decides on what it has and records assumptions |
| Answers are applied, not just logged | the asker's next version must carry the `## Clarifications` entries; submit-for-review is refused if a session is answered and unapplied |
| A session does not change the artifact's status | the artifact reports `waiting_on: <target>` while a session is open |
| A session is closed by the asker | when it applies the answers, or when the artifact is abandoned |

---

## Who asks whom

| Asker | Target | When |
|---|---|---|
| analyst | Product Owner | the spec is ambiguous on intent |
| planner | analyst | the approved spec is ambiguous on meaning; the analyst may in turn open a session with the Product Owner, and the answer flows back through a spec revision (which re-runs the Product Owner's approval only if a requirement changed) |
| reviewer | planner | the Plan is silent on something the checklist needs (silence is asked about; wrongness is rejected) |
| architect | Product Owner or Solution Architect | constitution derivation |

Humans never open sessions; a human with a question rejects with a reason.
