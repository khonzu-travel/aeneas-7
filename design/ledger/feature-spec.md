# Ledger — Feature Spec (`spec.md`)

The Feature Spec is the entry point of all work: structured human intent, the
"what" and "why", written so that its success is measurable and its stories
independently testable. It replaces the v6 Story and takes Spec Kit's
`spec.md` format.

**Owner**: `analyst` role
**Approver**: Product Owner

---

## Format

```markdown
# Feature Specification: <name>

**Feature**: F-0042 · **Branch**: feat/F-0042-<slug> · **Status**: [DRAFT]
**Priority**: 2 · **Type**: BUSINESS | TECHNICAL · **Created**: 2026-09-12
**Input**: <the Product Owner's intent, verbatim>

## User Scenarios & Testing

### User Story 1 — <title> (Priority: P1)
<narrative: as a <role>, I want <capability>, so that <benefit>>
**Why this priority**: ...
**Independent test**: <how this story alone is verified and delivers value>
**Acceptance scenarios**:
1. **Given** ..., **When** ..., **Then** ...
2. ...

### User Story 2 — <title> (Priority: P2)
...

### Edge Cases
- What happens when ...?
- How does the system handle ...?

## Requirements

### Functional Requirements
- **FR-001**: The system MUST ...
- **FR-002**: Users MUST be able to ...
- **FR-003**: The system MUST ... [NEEDS CLARIFICATION: <what is unknown>]

### Key Entities
- **<Entity>**: what it represents, key attributes, relationships (no schema)

## Success Criteria
- **SC-001**: <measurable, technology-agnostic outcome>
- **SC-002**: ...

## Constraints
- Measurable constraints stated at intake: limits, retention, accessibility
  level, what must never be shown. These are acceptance criteria, not solutions.

## Assumptions
- Scope boundaries and defaults taken where the input was silent.

## Clarifications
### Session 2026-09-12
- Q: <question> → A: <answer>

## Dependencies
- Predecessors: F-0031
```

---

## Rules the platform enforces on the format

| Check | When | Refusal |
|---|---|---|
| Every required section present; at least one user story with priority and at least one acceptance scenario | every submission | names the missing section |
| `FR-###` and `SC-###` numbered contiguously from 001 | every submission | names the gap |
| No `[NEEDS CLARIFICATION]` marker remains | submit-for-review | lists the markers |
| No implementation detail in a `BUSINESS` spec (a technology, a library, a schema) | submit-for-review, analyze pass | `HIGH` finding returned to the analyst |
| Every user story has an **Independent test** | submit-for-review | names the story |
| Priority 1–5 present | creation | refused |

The distinction the v6 Story documented in prose is now a check: a
*constraint* ("responses up to 100 MB must work") is an acceptance criterion
and belongs here; a *mechanism* ("stream to disk above 10 MB") is `HIGH` here
and belongs in the Plan.

---

## Statuses

| Status | Trigger | Meaning |
|---|---|---|
| `[DRAFT]` | `FeatureCreated`; `SpecRejected` → analyst revision | The analyst is authoring, possibly with an open clarification session |
| `[UNDER_REVIEW]` | analyst submit-for-review, format checks pass | The Product Owner holds the decision |
| `[APPROVED]` | Product Owner approves | Version pinned; a `plan` turn is enqueued |
| `[REJECTED]` | Product Owner rejects with reasons | Returned to `[DRAFT]` on the analyst's next version; `rejection_count` incremented |
| `[DONE]` | Plan integrated and released | The intent is realized |
| `[ABANDONED]` | Product Owner abandons the Feature | Terminal |

Reaching `MAX_SPEC_REJECTIONS` holds the Feature and asks the Product Owner to
revise the intent or abandon.

---

## Clarification

Before submitting, the analyst runs the `clarify` skill: it scans the spec
against the nine-category ambiguity taxonomy (functional scope, domain model,
interaction flows, non-functional requirements, integrations, edge cases,
constraints, terminology, completion signals), and asks the Product Owner at
most `MAX_CLARIFY_QUESTIONS` per session, each multiple-choice or short-answer,
each with a recommended answer. Answers are written into `## Clarifications`
and applied to the section they resolve. A session is bounded and there are at
most `MAX_CLARIFY_SESSIONS`; past that the analyst states assumptions in
`## Assumptions` and submits. See [`clarification.md`](clarification.md).

---

## Readership

The Feature Spec is readable by every role on the feature. The v6 Story
Firewall is gone: the acceptance scenarios *are* the tests, so the tester and
implementer read them. What replaces the firewall is Test Independence — the
tester authors and freezes acceptance tests before any implementer turn, and
an implementer diff that touches them fails verification.
