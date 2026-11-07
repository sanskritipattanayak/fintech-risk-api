---
name: secure-ship
description: Pre-commit security and quality gate, then commit, push and open a PR for human review. Use after spec-to-code or bugfix-pr finishes. Never merges and never deploys.
allowed-tools: Read, Grep, Glob, Bash(pytest*), Bash(ruff*), Bash(git status*), Bash(git diff*), Bash(git add*), Bash(git commit*), Bash(git push origin feat/*), Bash(git push origin fix/*), Bash(gh pr create*), Skill(fintech-data-check), Skill(security-review)
---

# secure-ship

## Scope
Final stage of both flows. Takes a finished branch to an open PR. **Merge and production deploy are human + CI actions, not Claude's.**

## Gate sequence (stop at the first failure)
1. `git diff` review: only files in the spec trace or incident scope changed.
2. `pytest -q` green, coverage not lower than baseline.
3. `fintech-data-check` = PASS.
4. Secret scan on the staged diff.
5. Dependency check: no new packages unless approved in spec.
6. `/security-review` on the diff via an independent subagent; any High finding blocks.
7. **Human gate G3**: show the diff summary and security findings; wait for explicit "ship".
8. Commit (small, focused, conventional message, attribution trailer), push the feature/fix branch only.
9. Open PR using the template: summary, spec or incident link, test evidence, security findings, rollback plan, risk label.

## Rules
- Never push to `main`, never `--force`, never rewrite history, never enable auto-merge.
- PRs touching limits, thresholds or model scoring get the `risk:high` label so CODEOWNERS require a risk-team reviewer.
- Deploy: after human merge, CI/CD (GitHub Actions) runs tests, SAST, dependency audit, then waits on the `production` environment's required reviewers. Claude has no deploy credentials.

## Hooks relied on
- `PreToolUse(Bash)`: denies `git push` to protected branches, `--force`, `rm -rf`, `curl`/`wget`.
- `PreToolUse(Bash: git commit)`: runs secret scan and tests; blocks on failure.
- `PostToolUse(Bash: gh pr create)`: logs PR URL to the audit trail.

## Done when
PR is open, all gates recorded in the PR body, and a human is the only path to merge.
