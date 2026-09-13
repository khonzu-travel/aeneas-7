# Ledger — Amendment

An Amendment is a governed change to the Constitution. It merges the v6
Petition (the request) and Amendment (the change record) into one artifact
with one lifecycle.

**Owner**: `architect` role
**Approvers**: Solution Architect, Enterprise Architect

---

## Format

```markdown
# Amendment A-0007: <title>

**Constitution**: 1.2.0 → 1.3.0 (MINOR) · **Triggered by**: F-0042 (plan@v1, analyze finding C2) | independent
**Status**: [UNDER_REVIEW]

## Problem
<what the Constitution prevents or fails to say, with the Plan or evidence that surfaced it>

## Proposed change
<the exact Articles and sections changed, as a diff against the current version>

## Impact
- Plans not yet integrated citing the affected capability or Article: F-0042, F-0045
- Approved Plans in Build: none

## Alternatives considered
```

---

## Statuses

| Status | Trigger | Meaning |
|---|---|---|
| `[DRAFT]` | analyze gate `CRITICAL` on a constitution gap enqueues an `amend` turn; or an independent proposal | The architect is authoring |
| `[UNDER_REVIEW]` | submit | Both humans hold decisions |
| `[APPROVED]` | both approve | The platform applies it in the same transaction: a new Constitution version, version bump per the declared level |
| `[APPLIED]` | applied | Terminal; an Amendment authorizes exactly one change |
| `[REJECTED]` | either rejects | Returned to the architect; the triggering Plan (if any) is returned to `[REJECTED]` with the reason, and its Feature Spec may need revision |
| `[ABANDONED]` | human decision | Terminal |

---

## Effect on open work

Applying an Amendment enqueues a re-analyze turn for every Plan not yet
integrated whose Constitution Check or Required Capabilities cite what changed
(`MINOR`), or for every such Plan (`MAJOR`). A Plan whose re-analyze returns
`CRITICAL` goes to `[REJECTED]` with the report. A Plan in Build that fails
re-analysis is held at the integration gate for the Solution Architect.

The Plan that triggered the Amendment waits at `[DRAFT]` with
`waiting_on: amendment A-0007` and resumes automatically when the Amendment is
applied.
