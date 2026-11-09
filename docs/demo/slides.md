---
marp: true
theme: default
paginate: true
---

<!-- Marp markdown: `npx @marp-team/marp-cli docs/demo/slides.md --pptx` (needs network for npx; run it outside the harness) or paste slide by slide into your deck. Speaker notes are the HTML comments. -->

# AI for the SDLC, inside the controls
Claude Code as the harness for a bank

<!-- Open: not a chatbot in an IDE. An agent that works through skills, under hooks, with humans at gates. -->

---

## The problem

- Banks want AI across the SDLC
- "Trust the model" is not a control
- Controls must be mechanical, logged, and independent of the model

<!-- Ask the CTO: what would your auditor need to see? -->

---

## The harness

| Capability | What it gives you |
|---|---|
| Skills | Repeatable, reviewable procedures with scoped tools |
| Hooks | Deterministic enforcement on every prompt and tool call |
| Subagents | Independent, read-only review |
| Headless | The same controls in automation |
| Audit | Hash-only decision log plus per-PR evidence |

<!-- Diagram: Harness overview in docs/demo/diagrams.md -->

---

## Six human gates

G1 spec · G2 plan · G3 ship · G4 triage · G5 PR review · G6 prod approval

Claude never merges, never deploys, never self-approves.

---

## Live: the guardrails block things

- Fake card number in a prompt: blocked
- Read `.env`: blocked
- Commit with red tests: blocked

<!-- Then show one audit.jsonl line: decisions, hashes only, no content. -->

---

## Flow 1: PRD to prod (recorded)

PRD → spec → **G1** → plan → **G2** → tests first → secure-ship → **G3** → PR → **G5** → CI → **G6**

<!-- Play recording R1, 3 minutes. -->

---

## Flow 2: log alert to fix PR

Declines spike after midnight UTC.

Synthetic traffic, real decision code: the symptom is genuine, not hand-edited.

<!-- Show the hour histogram from README 4a. -->

---

## Triage: evidence before opinion

- Redact first, then cluster by hour and decline reason
- Hypothesis: timezone handling in the velocity window
- Severity, impact, **auto_fix_eligible**

<!-- Live: /log-triage. Read the report aloud. This is G4. -->

---

## Headless: no human at the keyboard

`claude -p` without `--bare`: hooks still fire
Allow-listed tools · dollar cap · stops before commit

<!-- Play recording R3. Point at the allow-list in scripts/log_to_fix.sh. -->

---

## The fix: test first, minimal diff

- Failing regression test reproduces the midnight spike
- Fix removes the ledger mirroring, compares money as Decimal
- Strict xfail forced the guard test back on

<!-- git diff demo-start demo-fixed --stat -->

---

## Independent review

`security-reviewer` subagent: read-only tools, did not write the code

Any loosened control or test = **High** = blocked.

---

## Honest lessons

- A chained `git add && git commit` bypassed the first commit gate; CI caught it; we added three scan points
- The float-money hook is lexical; the seeded float compare passed it
- Not yet enforced: admin bypass off, required CI check

<!-- Candour is the credibility. -->

---

## Evidence: "What did the AI do?"

compliance-evidence pack per PR: controls exercised, gate approvals, test and security results, data-handling attestation.

---

## AI for SDLC, in one line

**Speed inside controls**: the agent proposes, hooks and humans dispose, and every step leaves evidence.
