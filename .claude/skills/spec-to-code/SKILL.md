---
name: spec-to-code
description: Implement an APPROVED spec test-first on a feature branch. Use after docs/specs/<feature>.spec.md has an Approved-by header. Refuses if the spec is unapproved.
allowed-tools: Read, Grep, Glob, Edit(app/*), Edit(tests/*), Bash(pytest *), Bash(ruff *), Bash(git checkout -b *), Bash(git status *), Bash(git diff *)
---

# spec-to-code

## Scope
Flow 1, stage 2. Turns an approved spec into code and tests on a branch `feat/<feature>`. Does not commit or push; that is `secure-ship`.

## Preconditions
- Spec has `Approved-by:`. If not, stop and say so.
- Working tree clean; not on `main`.

## Steps
1. Enter plan mode; propose a file-level change list mapped to acceptance criteria. Human approves the plan (gate G2).
2. For each acceptance criterion: write the failing test, then the minimum code to pass.
3. Enforce conventions: `Decimal` money (never float), tz-aware UTC, type hints on public functions, structured logs with no PII.
4. Run `pytest -q` and `ruff`. Iterate until green.
5. Produce `docs/specs/<feature>.trace.md`: criterion → test name → code location.
6. Hand off to `secure-ship`.

## Rules
- Do not edit the spec. If the spec is wrong, stop and raise it.
- Do not add dependencies without asking.
- Do not weaken or delete existing tests.
- Synthetic data only; any new fixture goes through `fintech-data-check`.

## Hooks relied on
- `PostToolUse` on Edit/Write: DLP scan of the written file, ruff (incl. naive-datetime rule) and a float-for-money check. Tests are gated at commit and at `Stop`, so red-first TDD still works.
- `PreToolUse`: blocks reads of `.env` and `secrets/`, blocks network tools.
- `Stop`: refuses to end the turn with failing tests.

## Done when
All acceptance criteria have passing tests, trace file written, no hook failures outstanding.
