---
name: compliance-evidence
description: Assemble an audit-ready evidence pack for a PR (controls exercised, gate approvals, test and security results, data-handling attestations). Use at the end of secure-ship for both flows, or when an auditor asks what the AI did.
allowed-tools: Read, Grep, Glob, Edit(evidence/*), Skill(fintech-data-check)
---

# compliance-evidence

## Scope
Read-only collector plus one writer: produces `evidence/<pr-or-incident-id>.md`, attached to the PR. Never edits source. Makes no certification claims; states which controls were exercised and leaves validation to the compliance team.

## Collects
1. **Change record**: spec or incident link, trace file, branch, diff hash, files touched.
2. **Data handling**: `fintech-data-check` result; data classes touched; confirmation no restricted data entered prompts, logs or fixtures; canary suite result.
3. **Access**: tools and paths used vs allow-list; any hook denials (what, when, which rule).
4. **Quality and security**: pytest and coverage, SAST, dependency audit, secret scan, independent `/security-review` findings and dispositions.
5. **Approvals**: G1-G6 with approver identity and timestamp; confirm author, reviewer and prod approver are different people (separation of duties).
6. **Risk**: `risk:high` label present for limits, thresholds or model changes; risk-team approval recorded.
7. **Rollback**: documented plan and flag.
8. **Control map**: table of the controls exercised, mapped to PCI DSS / SOC 2 / GLBA / model-risk areas as indicative references.

## Rules
- Evidence comes from artefacts (audit log, CI output, PR metadata), never from memory or assumption. Missing artefact is reported as `MISSING`, not inferred.
- Do not include raw prompts or any restricted data; use hashes and counts.
- Timestamps timezone-aware UTC.

## Hooks relied on
`PostToolUse(Bash: gh pr create)` writes the audit-log entries this skill reads; `PreToolUse` deny events are logged for step 3.

## Human gate
Evidence pack is reviewed as part of G5; a `MISSING` item blocks merge via a required CI check.

## Done when
Pack exists, every section is populated or flagged `MISSING`, and it is linked in the PR body.
