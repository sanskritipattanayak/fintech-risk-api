---
name: fintech-data-check
description: Verify that data, fixtures, logs and diffs contain only synthetic data and obey money/time rules. Use before committing, before sending logs to a model, and when adding fixtures. Shared by both flows.
allowed-tools: Read, Grep, Glob, Bash(pytest*), Bash(python -I*)
---

# fintech-data-check

## Scope
Read-only validator used by every other skill. Reports pass/fail with file and line; never edits.

## Design stance
Written as if the data were real and restricted. Synthetic data is the safe stand-in for the demo; the checks must still be strong enough for production. Classify first: `public`, `internal`, `confidential`, `restricted` (PAN, SSN, account numbers, full names + DOB). Restricted data is never allowed in prompts, logs, fixtures, diffs or incident reports; only tokens.

## Checks
0. **Canaries**: planted fake PAN, SSN and key values (kept in `tests/canary/`) must be detected wherever they appear; a missed canary is a failing check and the detector itself is considered broken.
1. **No real PII**: no Luhn-valid PANs, SSN/ABA/IBAN patterns, emails or phone numbers outside an allow-listed synthetic domain (`example.test`). Card ids must match `card_[0-9a-f]{8}`.
2. **No secrets**: API keys, tokens, private keys, `.env`-style assignments. Never open `.env` or `secrets/`; scan only tracked source, data and logs.
3. **Money**: no `float` for amounts; DB/CSV amounts are decimal strings; rounding mode is explicit.
4. **Time**: no naive `datetime.now()` / `utcnow()`; all parsing yields tz-aware UTC.
5. **Data shape**: `data/transactions.csv` schema, no nulls in key columns, amounts non-negative, timestamps monotonic per card, class balance sane for the model.
6. **Log hygiene**: logs have no raw card ids beyond the token, no request bodies.

## Output
A short table: check, status, evidence (path:line). Exit non-zero summary line `DATA_CHECK: FAIL` or `DATA_CHECK: PASS`.

## Used by
`spec-to-code` (fixtures), `secure-ship` (pre-commit gate), `log-triage` (redact before analysis), `bugfix-pr` (before opening PR).

## Out of scope
Fixing violations. Report them; the calling skill decides.
