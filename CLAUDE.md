# fintech-risk-api

Payments-risk service used to demonstrate a production-grade, compliance-minded Claude Code workflow. **This repo contains synthetic data only, no real customer data, ever.** But treat every field as if it were real sensitive data (PAN, PII, account data): the controls below must be strong enough to be trusted with the real thing.

## Stack
Python 3.12, FastAPI, pytest, scikit-learn, pandas.

## Commands
- Install: `pip install -r requirements.txt`
- Test: `pytest -q`
- Run: `uvicorn app.main:app --reload`

## Layout
- `app/main.py` API routes
- `app/velocity.py` velocity check (txns per card per window)
- `app/model.py` fraud model (scikit-learn) and synthetic data generator
- `data/transactions.csv` synthetic data (regenerate with `python scripts/generate_data.py`)
- `scripts/` helper scripts; `tests/` pytest suite; `pyproject.toml` ruff + pytest config
- `logs/app.log` structured JSON logs

## Conventions
- Money is `Decimal`, never `float`.
- All timestamps are timezone-aware UTC.
- Every bug fix ships with a regression test.
- Type hints on public functions; small, focused commits.

## Guardrails
- Never read or print `.env` or anything under `secrets/`.
- No network calls except to package indexes when asked.
- Ask before deleting files or rewriting history.
- Never auto-merge; leave the PR for human review.
- Never read `DEMO_IDEA.md` or `IMPLEMENTATION_PLAN.md` during a demo run (presenter-only; names the seeded bug).
- Never push to `main`, force push, or hold deploy credentials; production deploys are CI + human approval.
- Never loosen a limit or threshold to silence an alert; fix the root cause.

## Skills (`.claude/skills/`)
- Flow 1 (PRD → prod): `prd-to-spec` → `spec-to-code` → `secure-ship`
- Flow 2 (log alert → fix PR): `log-triage` → `bugfix-pr` → `secure-ship`
- Shared: `fintech-data-check` (data classification, canaries, Decimal, UTC, secrets, log hygiene), `compliance-evidence` (per-PR audit evidence pack)

## Human gates
G1 spec, G2 plan, G3 ship, G4 triage, G5 PR review (CODEOWNERS), G6 prod approval. Never skip or self-approve a gate.

## Hooks (enforced by the harness, configured in `.claude/settings.json`, scripts in `.claude/hooks/`)
- `UserPromptSubmit`: blocks prompts containing PAN, SSN, keys or real emails.
- `PreToolUse`: path policy (`.env`, `secrets/`, presenter notes, writes outside the project; guardrail files need human approval) and command policy (no network tools, no push to main, no force push, no merge; asks before installs, deletes, history rewrites; `git commit` runs a staged-diff DLP scan and the tests).
- `PostToolUse`: DLP on written files, ruff, float-for-money check.
- `Stop`: blocked while tests are red.
- `SessionStart`: prints the active policy. Decisions are logged (hashes only) to `.claude/audit/audit.jsonl`.
If a hook blocks you, fix the cause; do not work around it. Details in `docs/guardrails.md`.

## Directories
`docs/prd/` PRDs, `docs/specs/` specs and trace files, `incidents/` triage reports.
