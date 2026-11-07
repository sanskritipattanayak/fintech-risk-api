---
name: log-triage
description: Read structured app logs, cluster errors and anomalies, and produce a redacted incident report with a root-cause hypothesis and severity. Use when an alert fires or the user asks why declines/errors spiked. Read-only.
allowed-tools: Read(logs/*), Grep, Glob, Skill(fintech-data-check), Write(incidents/*)
---

# log-triage

## Scope
Flow 2, stage 1. Analyses `logs/app.log`, writes `incidents/<id>.md`. Never edits source.

## Steps
1. Redact first: run `fintech-data-check` log-hygiene; work only on the redacted view.
2. Bucket events by `event`, `error_code`, minute; compare to baseline hour/day.
3. Cluster by signature (exception type + top frame, or decline reason).
4. Correlate with recent commits (`git log`, read-only) and deploy markers.
5. Form a root-cause hypothesis with evidence (log line refs, counts, first-seen time) and a confidence level.
6. Classify: `severity` (S1-S4), `customer_impact` (e.g. false declines, missed fraud), `money_at_risk` (synthetic estimate), `auto_fix_eligible` (true only for deterministic code defects with a clear test).

## Output (`incidents/<id>.md`)
Title, timeline, signature, evidence, hypothesis, severity, impact, eligibility, recommended next action.

## Human gates
- **G4 (alert triage)**: S1/S2 or `auto_fix_eligible=false` pages on-call and the pipeline stops.
- **G4b**: eligible incidents proceed to `bugfix-pr` automatically, but the PR still needs human review.

## Hooks relied on
- `PreToolUse`: blocks reads outside `logs/` and `incidents/`; blocks `.env` and `secrets/`.
- `PostToolUse(Write)`: runs redaction lint on the incident file.

## Out of scope
Fixing, restarting services, touching infra, any network call.
