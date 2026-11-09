---
name: bugfix-pr
description: Given an auto-fix-eligible incident report, reproduce with a failing test, make the minimal fix, and hand off to secure-ship for a PR. Runs headless in the automated pipeline or interactively.
allowed-tools: Read, Grep, Glob, Edit(app/*), Edit(tests/*), Bash(pytest *), Bash(ruff *), Bash(git checkout -b fix/*), Bash(git diff *), Skill(fintech-data-check), Skill(secure-ship)
---

# bugfix-pr

## Scope
Flow 2, stage 2. Input: `incidents/<id>.md` with `auto_fix_eligible: true`. Output: branch `fix/<id>` and an open PR (via `secure-ship`).

## Steps
1. Verify eligibility and that the incident file passed redaction lint.
2. Create worktree/branch `fix/<id>` from the latest `main`.
3. Write a **failing regression test** that reproduces the bug from the evidence (boundary timestamps, float vs `Decimal`). Confirm it fails for the right reason.
4. Minimal fix. No refactors, no unrelated changes. Keep the diff small.
5. Run full `pytest -q` and `ruff`. Regression test must now pass.
6. Blast-radius check: list other call sites with the same pattern; report, do not silently fix.
7. Invoke `secure-ship` (includes independent security review).
8. PR body: incident link, root cause, fix, test evidence, rollback, `risk` label.

## Guardrails
- Diff budget: abort and escalate if the fix touches more than 3 files or 80 lines, or any file outside `app/` and `tests/`.
- Never loosen a threshold or limit to "make declines stop"; fixes must be root-cause code fixes.
- If the failing test cannot be written, stop and escalate to a human. No test, no fix.
- Headless runs use a restricted tool allow-list, no network, a turn cap and a cost cap.

## Human gates
- **G5**: human PR review with CODEOWNERS. Only a human merges.
- Pipeline posts the result (PR link or escalation) to on-call.

## Hooks relied on
`PreToolUse` (path and command deny rules), `PostToolUse` (lint, tests), `Stop` (no finish with red tests), and a final audit-log hook recording prompt, tools and diff hash.

## Done when
Regression test fails before and passes after, PR is open, on-call is notified.
