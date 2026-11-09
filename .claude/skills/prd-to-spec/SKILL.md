---
name: prd-to-spec
description: Turn a product requirements doc (PRD) into a reviewable engineering spec with fintech acceptance criteria, data classification and a test plan. Use when a PRD or feature request is dropped in docs/prd/ or the user says "spec this". Stops for human approval before any code.
allowed-tools: Read, Grep, Glob, Edit(docs/specs/*)
---

# prd-to-spec

## Scope
Flow 1, stage 1. Converts `docs/prd/<feature>.md` into `docs/specs/<feature>.spec.md`. **Writes only the spec. Never touches `app/` or `tests/`.**

## Inputs
- A PRD (problem, users, success metric, constraints).
- `CLAUDE.md` conventions and existing code layout (read-only).

## Output: spec file sections (all required)
1. **Summary and non-goals**
2. **API contract**: routes, request/response models, error codes.
3. **Money and time rules**: `Decimal` amounts, quantisation and rounding mode, tz-aware UTC timestamps.
4. **Data classification**: every field tagged `synthetic-public` / `pseudo-id` / `sensitive`. Anything that looks like a real PAN, SSN or name is rejected. Card ids are opaque tokens.
5. **Risk and abuse cases**: what a fraudster or a buggy client can do (replay, boundary-of-window, negative amounts, currency mismatch).
6. **Audit and logging**: which structured events are emitted; confirm no PII in logs.
7. **Acceptance criteria**: numbered, each testable as one pytest case. Include boundary cases (midnight UTC, limit equal to amount).
8. **Test plan**: unit, API, property tests, regression cases.
9. **Rollout and rollback**: feature flag, shadow mode, how to revert.
10. **Open questions** for the human.

## Steps
1. Read PRD and relevant code. Do not guess requirements; list gaps under Open questions.
2. Draft the spec.
3. Self-check: every PRD requirement maps to at least one acceptance criterion (add a traceability table).
4. Stop and ask the human to approve.

## Human gate (G1: spec approval)
The spec must be approved by a named human (record `Approved-by:` in the file header). `spec-to-code` refuses to run on an unapproved spec.

## Hooks relied on
- `UserPromptSubmit`: PII scan on pasted PRD text.
- `PreToolUse`: blocks writes outside `docs/specs/`.

## Out of scope
Implementation, dependency choices beyond the stack in CLAUDE.md, network calls.

## Done when
Spec exists, traceability table is complete, open questions are listed, and approval is pending or recorded.
