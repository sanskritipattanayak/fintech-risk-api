# fintech-risk-api: Claude Code as the AI-for-SDLC harness

A small payments-risk service (synthetic data only) built to show how a bank can let an AI agent work across the software lifecycle **with the controls already in place**: skills as repeatable procedures, hooks as enforcement, subagents for independent review, headless mode for automation, and an audit trail for compliance.

> The product is not the app. The product is the loop: **alert or PRD in, reviewed PR out, every step gated and logged.**

Contents: [1. The app](#1-the-app-what-was-built) · [2. The harness](#2-the-harness-what-makes-it-safe) · [3. Flow 1](#3-flow-1-prd-to-prod-recorded-3-min) · [4. Flow 2](#4-flow-2-log-alert-to-fix-pr-the-deep-dive) · [5. Speaker flow](#5-speaker-flow-30-min) · [6. Recording plan](#6-what-to-record-and-how) · [7. Budget](#7-budget-and-model-choices) · [8. Do not claim](#8-do-not-claim-in-the-room) · [9. Reset](#9-reset-and-rehearsal)

Diagrams: [docs/demo/diagrams.md](docs/demo/diagrams.md). Slides: `docs/demo/slides.pptx` (build with `scripts/build_deck.js`, needs Node; speaker notes are in the file). The earlier outline is kept in [docs/demo/slides.md](docs/demo/slides.md). Guardrail layers: [docs/guardrails.md](docs/guardrails.md).

---

## 1. The app: what was built

Stack: Python 3.12, FastAPI, scikit-learn, pandas, pytest, ruff.

| Piece | File | What it does |
|---|---|---|
| API | `app/main.py` | `POST /score` validates (card id pattern, `Decimal` amount, tz-aware timestamp) and returns a decision; `GET /health` |
| Decision | `app/decision.py` | Velocity check first, then the fraud model. One function shared by the API and the simulator |
| Velocity | `app/velocity.py` | Max 5 txns per card per sliding 10-minute window, UTC only, naive datetimes rejected |
| Model | `app/model.py` | scikit-learn fraud model trained on synthetic data (`data/transactions.csv`) |
| Logging | `app/logging_config.py` | JSON event log with an **allow-list** of fields: no bodies, no PII |
| Simulator | `app/simulate.py` | Pushes 24h of synthetic traffic through the **real** decision code, so a defect shows up as a genuine log symptom |
| Tests | `tests/` | Unit, API, logging, simulator, and `tests/canary/` (seeded fake PAN/SSN/keys that the DLP must catch) |

Conventions that the harness enforces: money is `Decimal`, timestamps are tz-aware UTC, every bug fix ships a regression test.

Run it:

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

```bash
curl -s localhost:8000/health
```

### The seeded defect (demo-start state)

`app/velocity.py` carries a deliberate defect for Flow 2:
1. **Local time vs UTC**: a "ledger day" derived from a UTC-5 offset mirrors events into extra buckets whenever the ledger date lags the UTC date (00:00 to 05:00 UTC). Counts inflate, so cards are falsely declined.
2. **Float money compare**: `amount_exceeds_limit` compares via `float()`. Latent (not on the decision path today), found by the blast-radius step.

Symptom in `logs/app.log` (regenerated from the real code): `DECLINED_VELOCITY` jumps from about 20 per day to 43, with 26 of them between 00:00 and 05:00 UTC, starting at the UTC midnight boundary. Regenerate with `python scripts/generate_logs.py`.

The one existing guard test, `test_correct_code_has_no_midnight_spike`, is marked `xfail(strict=True)` with the reason "seeded demo defect". `strict=True` means the test **fails loudly the moment the bug is fixed**, which forces whoever fixes it to remove the marker. The fix PR does exactly that.

---

## 2. The harness: what makes it safe

| Capability | Where | Demo moment |
|---|---|---|
| **Skills** | `.claude/skills/`: `prd-to-spec`, `spec-to-code`, `log-triage`, `bugfix-pr`, `secure-ship`, `fintech-data-check`, `compliance-evidence` | Each flow is a chain of skills; each skill declares its own `allowed-tools` |
| **Hooks** | `.claude/hooks/`, wired in `.claude/settings.json` | Paste a fake card number into a prompt: blocked. Ask it to read `.env`: blocked. `git commit` with red tests: blocked |
| **Subagents** | `.claude/agents/security-reviewer.md` | Independent, read-only reviewer with an explicit tool list; it did not write the code |
| **Headless mode** | `scripts/log_to_fix.sh` (`claude -p`, no `--bare`) | Same hooks fire in CI-style runs; tool allow-list and dollar cap per stage |
| **Plan mode** | interactive, before `spec-to-code` | Review the plan at gate G2 before anything is edited |
| **Audit trail** | `.claude/audit/audit.jsonl` (hashes only), `compliance-evidence` skill | "What did the AI do?" answered per PR |
| **Human gates** | G1 spec, G2 plan, G3 ship, G4 triage, G5 PR review (CODEOWNERS), G6 prod approval | Claude never merges, never deploys, never self-approves |

Layered controls (details in `docs/guardrails.md`): org policy, permission rules, hooks, commit/push/PR gate, git hooks (survive `--no-verify`), CI re-scan, CODEOWNERS plus branch protection.

**Honest lesson to tell:** a chained `git add -A && git commit` slipped a PAN-shaped literal past the first commit gate because nothing was staged when the hook ran. CI caught it. The fix added working-tree and outgoing-commit scans plus real git hooks, with regression tests in `tests/canary/test_gates.py`. Defence in depth, found by testing the controls, not assuming them.

---

## 3. Flow 1: PRD to prod (recorded, ~3 min)

```
PRD in docs/prd/  ->  prd-to-spec  ->  [G1 spec approval]  ->  plan mode  ->  [G2]
  ->  spec-to-code (tests first)  ->  secure-ship  ->  [G3]  ->  PR  ->  [G5 CODEOWNERS]
  ->  CI  ->  [G6 production environment approval]  ->  deploy (CI, not Claude)
```

**Trigger:** put a short PRD in `docs/prd/` (for example "add a per-card daily amount cap, Decimal, UTC day") and, in an interactive session:

```text
Spec this PRD: docs/prd/<name>.md
```

Approve the spec by adding the `Approved-by` header yourself (that is gate G1; `spec-to-code` refuses without it), then:

```text
Implement docs/specs/<name>.spec.md
```

Switch to plan mode (Shift+Tab) for G2 before it edits. Finish with the `secure-ship` skill, which stops at G3 and waits for an explicit "ship".

**Record this one**, edit to 3 minutes, narrate over the [Flow 1 diagram](docs/demo/diagrams.md#flow-1-prd-to-prod).

---

## 4. Flow 2: log alert to fix PR (the deep dive)

```
logs/app.log  ->  log-triage (haiku, read-only)  ->  [G4 eligibility]
  ->  bugfix-pr (failing test, minimal fix)  ->  secure-ship  ->  security-reviewer subagent
  ->  [G3 ship]  ->  PR  ->  [G5 human review]  ->  compliance-evidence pack
```

### 4a. Show the alert (live, free)

```bash
python scripts/generate_logs.py
```

Then show the hour-by-hour decline count (no model call):

```bash
python3 -c "import json,collections;c=collections.Counter(json.loads(l)['ts'][11:13] for l in open('logs/app.log') if 'DECLINED_VELOCITY' in l);print(sorted(c.items()))"
```

Point at hours 02 to 04: this is the "alert".

### 4b. Triage (live, interactive, cheap)

```text
/log-triage why did velocity declines spike overnight?
```

Expect: redaction first, clustering by hour, hypothesis pointing at timezone handling in `app/velocity.py`, severity, `auto_fix_eligible: true`, report in `incidents/`. G4: read the report aloud.

### 4c. Headless pipeline (record, do not run live)

```bash
scripts/log_to_fix.sh INC-DEMO-001
```

What the script does and why it is safe to show a CTO:
- `claude -p` **without `--bare`**, so every hook still fires (`--bare` skips them; documented in `docs/guardrails.md`).
- Stage 1 on `haiku` with a read-only allow-list and `--max-budget-usd 0.50`; stage 2 on `sonnet` with edit rights only under `app/` and `tests/`, `--max-budget-usd 1.50`.
- A scripted G4 check parses `auto_fix_eligible`; if false it exits and tells you to page on-call.
- It stops **before** commit/push/PR. Shipping is a separate, human-gated step.
- Raw run output goes to `.claude/audit/runs/` (git-ignored).

### 4d. The fix and regression test (the reference answer)

The branch `demo-fixed` holds the expected result: remove the bogus ledger mirroring, compare money as `Decimal`, add regression tests, remove the `xfail`. Use it for the slide and as a fallback if a live run misbehaves:

```bash
git diff demo-start demo-fixed --stat
```

### 4e. Ship and review

In the interactive session: run `secure-ship`. It runs tests, `fintech-data-check`, a secret scan, then invokes the `security-reviewer` subagent on the diff, then **stops at G3**. After "ship" it commits (hooks run DLP + tests), pushes the `fix/` branch, and opens a PR with `gh pr create`. A human (`sanskritip-png`) reviews, CI runs, the `production` environment waits for the reviewer. Close with:

```text
Run compliance-evidence for this PR
```

---

## 5. Speaker flow (30 min)

| Min | Slide / action | Message |
|---|---|---|
| 0-3 | Problem framing | Banks want AI in the SDLC but cannot accept "trust the model". Controls must be mechanical |
| 3-6 | Harness diagram | Skills, hooks, subagents, headless, audit; humans at six gates |
| 6-9 | Guardrail demo (live) | Prompt with a fake card number: blocked. `.env` read: blocked. Show `audit.jsonl` entry (hashes only) |
| 9-12 | Flow 1 recording | PRD to PR in 3 minutes; stress G1/G2 are human |
| 12-15 | Flow 2 setup | Show the symptom in the log (4a) |
| 15-20 | Triage live (4b) | Redaction first; evidence-based report; G4 |
| 20-24 | Headless recording (4c) | Same hooks without a human at the keyboard; caps and allow-lists |
| 24-27 | Fix diff + security-reviewer (4d, 4e) | Test first, minimal diff, independent review, loosened-test would be High |
| 27-30 | Evidence pack + close | "What did the AI do?" answered in one document; AI for SDLC = speed inside controls |

Lines worth saying:
- "The agent proposes; hooks and humans dispose."
- "Fixing the bug removed an `xfail` I had added. The system told me to, because the marker was strict."
- "We tested the guardrails and one failed. That is the point of the canary suite."

---

## 6. What to record and how

| # | Recording | Length | How | Cost (rough estimate) |
|---|---|---|---|---|
| R1 | Flow 1, PRD to PR | 3 min | Interactive session, screen record, cut dead time | ~$1-2 |
| R2 | Guardrail blocks (prompt DLP, `.env`, commit with red tests) | 2 min | Interactive; these are blocked before any model work | ~$0.10 |
| R3 | Flow 2 headless pipeline | 3 min | `scripts/log_to_fix.sh INC-DEMO-001` once | ~$1-2 |
| R4 | secure-ship with security-reviewer, PR open | 3 min | Interactive on the `fix/` branch | ~$1 |
| R5 | compliance-evidence output | 1 min | Interactive | ~$0.30 |

Record more, rehearse less: do one clean take of each, keep the raw `.claude/audit/runs/*.json` as proof of cost and tool use. Live in the room: 4a, 4b only.

Before recording, in a terminal: `git checkout demo-start` (or the main tag), `git checkout -b fix/INC-DEMO-001`.

---

## 7. Budget and model choices

About $20 remains. Defaults in `scripts/log_to_fix.sh`: triage `haiku` $0.50, fix `sonnet` $1.50, overridable via `TRIAGE_MODEL`, `FIX_MODEL`, `TRIAGE_BUDGET`, `FIX_BUDGET`. Routine steps (triage, evidence) on the cheaper model; code changes on the stronger one.

---

## 8. Do not claim in the room

Unverified (also listed in `docs/guardrails.md`):
- Whether `allowManagedHooksOnly` also blocks a developer setting `disableAllHooks`.
- `Skill(...)` permission-rule syntax. The skills' `allowed-tools` lines use it; treat as unverified.
- How to force a specific subagent in non-interactive mode. `claude --agent <name>` exists in 2.1.319's `--help` ("agent for the current session") but headless behaviour is untested here.
- `--max-turns`: the brief called for it, but it does **not** appear in `claude --help` for 2.1.319. The script therefore relies on `--max-budget-usd` and only passes `--max-turns` if you set `CLAUDE_MAX_TURNS`. Verify before saying "turn-capped".
- The hook that flags float money is **lexical** (it matches money-ish variable names). The seeded float compare uses neutral names and passes it. That is a real gap, a good "defence in depth" talking point, and the reason the security-reviewer checks for it too.
- Not yet on in GitHub: admin enforcement and the required CI check. Do not say "no one can bypass main".

---

## 9. Reset and rehearsal

| Tag / branch | Meaning |
|---|---|
| `demo-start` | `main` after the Phase 5 PR is merged: bug seeded, pipeline and agent present |
| `demo-fixed` | Reference fix: regression tests plus the fix |

Every run (rehearsal, recording, live) happens in a **throwaway git worktree** cut from `demo-start`, so your real checkout is never modified and a reset is exact:

```bash
scripts/demo_reset.sh start
```

```bash
scripts/demo_reset.sh reset
```

`start` creates `../fintech-risk-demo-run` on branch `fix/INC-DEMO-001` (with `.venv` linked). `cd` there and run `claude` or `scripts/log_to_fix.sh`. `reset` removes the worktree and the local fix branch after a y/N prompt, then `start` again gives a clean take. Run these yourself in a terminal; `reset` deletes, so the harness would (correctly) ask a human anyway.

What a reset does **not** undo, and what to do:
- **A pushed `fix/` branch or open PR**: close the PR and delete the remote branch on GitHub. For a live demo, push under a new id (`scripts/demo_reset.sh start INC-DEMO-002`) instead of reusing one.
- **Model spend**: nothing refunds it. Cap env vars apply on every run.
- **Audit trail**: `.claude/audit/` is git-ignored and lives in the worktree, so it is discarded with it. Copy `.claude/audit/` out first if you want it as evidence for a recording.

One-time setup after merging the Phase 5 PR: `git tag demo-start <merge commit on main>` and `git branch demo-fixed <fix commit>`. Never move the `demo-start` tag.

Rehearse with free steps only (`pytest -q`, `generate_logs.py`, the decline histogram). Run models only for the recordings.
