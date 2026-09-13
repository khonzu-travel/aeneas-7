# Workflows — Blocked

Blocked is a condition on an artifact, not a status. A blocker is a row in
the registry naming the artifact, the reason, the raiser, and the human role
that owns clearing it.

```
raiser (a turn or the platform) → BlockerRaised { artifact, reason, resume_context }
platform:
   machine-resolvable? (a predecessor now DONE, a reservation released, a stand-down cleared,
                        a budget raised) → BlockerCleared(cleared_by: platform) immediately
   else → owner_role by rule → that human's inbox
human clears with a resolution → BlockerCleared → the platform enqueues the turn that resumes
   the work, carrying resume_context
```

| Raised by | Typical reason | Owner |
|---|---|---|
| implementer turn | the Plan is ambiguous at a point a task needs | Delivery Lead (usually becomes a Defect) |
| verifier | `MAX_VERIFY_ATTEMPTS`, `MAX_INTEGRATION_ATTEMPTS` | Delivery Lead |
| platform | `BUDGET_EXHAUSTED` | Product Owner |
| platform | `DeploymentFailed` | Delivery Lead |
| platform | reservation collision at integration | Delivery Lead |
| Solution Architect | integration risk rejected | Delivery Lead |

While blocked, an artifact keeps its status and its tasks stay off `[READY]`;
the scheduler holds a blocked feature; the dashboard shows `blocked: true`
with the reason and owner. Clearing resumes exactly where the raiser stopped,
because the resuming turn is derived from the artifact's state and the
recorded context.
