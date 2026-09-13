# Pipeline — Phase 6: Operate

**Purpose**: observe the live system and route what it finds back into the
pipeline.
**Roles**: `operator`; the Delivery Lead and Product Owner decide.
**Input**: telemetry, deployment records.
**Output**: anomaly records; new Features.

---

## Flow

1. Anomaly rules (error rates, latency baselines from the Constitution's
   Non-Functional Baselines, health checks) fire; the platform enqueues
   `observe`.
2. An operator turn runs the `observe` skill: it reads the telemetry window,
   records an anomaly with severity and evidence (`AnomalyRecorded` on the
   platform stream), and links the deployment it followed.
3. Routing is by rule: `CRITICAL` → Delivery Lead inbox with a rollback
   recommendation the `release` skill can execute on decision; `HIGH` /
   `MEDIUM` → Product Owner inbox as a proposed Feature (intent pre-filled from
   the evidence); `LOW` → dashboard only.
4. A change to the system is a new Feature through Phase 1. The operator
   never writes code, configuration, or infrastructure.

---

## Constraints

- **No self-remediation**: the `operator` role's only write is an anomaly
  record.
- A rollback is a Delivery Lead decision executed by a `release` turn and
  recorded like any deployment.
