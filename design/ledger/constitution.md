# Ledger — Constitution

The Constitution is the project's architectural constitution: the principles
every Plan must satisfy and the vocabulary every Plan may use. It replaces the
v6 Archetype and takes Spec Kit's `constitution.md` shape, extended with the
sections the platform reads mechanically.

**Owner**: `architect` role
**Approvers**: Solution Architect, Enterprise Architect

---

## Role in the pipeline

```
Charter [APPROVED] ─▶ architect · constitution skill ─▶ Constitution [DRAFT]
                                                          │ submit
                                                          ▼
                                     Solution Architect + Enterprise Architect
                                                          │ both approve
                                                          ▼
                                                 Constitution [APPROVED]
                                                          │
                                        Feature delivery may begin
```

No Feature may be created until the Constitution is `[APPROVED]`. After that
it changes only by an applied [Amendment](amendment.md).

---

## Format

```markdown
# <Project> Constitution

**Version**: 1.3.0 · **Ratified**: 2026-09-01 · **Last amended**: 2026-09-12 (A-0007)

## Core Principles

### Article I — <name>
<principle stated as MUST / MUST NOT / SHOULD, with its rationale>

### Article II — <name>
...

## Capability Map
| Identifier | Capability | Scope | Status |
|---|---|---|---|
| CAP-AUTH | Authentication and session management | ... | GRANTED |

## Technology Stack
| Layer | Choice | Version constraint | Notes |

## Data Design Language
- Naming, identity, representation, constraint and sensitivity conventions
- The **representation contract**: the schema a `data-model.md` declaration must satisfy

## Security Model
- Trust boundaries, control catalog (`CTL-###`), threat surfaces (`TS-###`),
  the `controlCoverage` shape a `threat-model.md` must carry

## Interface Conventions
- API style, error shape, UI/accessibility level

## Non-Functional Baselines
| Concern | Baseline | Measured by |

## Operational Model
- Environments, deployment, observability, rollback

## Integration Landscape
| System | Contract | Owner |

## Compliance Mandates
| Regulation | Obligations | Evidence |

## Approved Patterns and Anti-Patterns

## Governance
- How this document changes (Amendment), versioning policy (semver), what a
  Plan's Constitution Check must answer
```

Articles carry the `MUST` language the analyze gate treats as `CRITICAL` when
violated. The remaining sections are the platform-read vocabulary: the
Capability Map is what `plan.md`'s `## Required Capabilities` is checked
against; the Data Design Language's representation contract is what
`data-model.md` declarations are validated against; the Security Model's
control catalog is what `threat-model.md`'s coverage block is computed
against.

---

## Versioning

The Constitution is versioned as one document. Semantic versioning is stated in
the document and enforced by the platform on an Amendment: a change that
removes or redefines an Article or a granted capability is `MAJOR`; one that
adds an Article, capability, or constraint is `MINOR`; wording is `PATCH`. A
`MAJOR` Amendment enqueues a re-analyze turn on every Plan not yet integrated;
a `MINOR` one does the same only for Plans whose `## Required Capabilities` or
Constitution Check cites what changed; a `PATCH` enqueues nothing.

---

## Statuses

| Status | Meaning |
|---|---|
| `[DRAFT]` | The architect is deriving it from the approved Charter, or revising after rejection |
| `[UNDER_REVIEW]` | Submitted; both human decisions open |
| `[APPROVED]` | In force. Further change is by Amendment only |
| `[REJECTED]` | A human rejected; returned with every reason |

---

## Readership

Every role and every human reads the Constitution. Authoring is the
architect's alone; approval is the two humans'.
