# Guardrails: how the controls are layered

Each layer works on its own, so one failure does not open a leak.

| Layer | Where | Enforced by | Developer can disable? |
|---|---|---|---|
| Org policy | `managed-settings.json` (see `managed-settings.example.json`) | Claude Code itself | No, when `allowManagedHooksOnly` and `allowManagedPermissionRulesOnly` are set |
| Permission rules | `.claude/settings.json` `permissions.deny` | Claude Code | Yes in a local checkout, unless org policy overrides |
| Hooks | `.claude/hooks/*.py` | Run on every tool call, prompt, stop | Same as above |
| Commit / push / PR gate | `guard_bash.py` on `git commit`, `git push`, `gh pr create` | PreToolUse hook: scans working tree and outgoing commits, runs tests | Same as above |
| Git hooks | `.githooks/pre-commit`, `pre-push` | git itself, any client (set via `core.hooksPath`) | Yes locally with `--no-verify`, which is why CI re-scans |
| CI | `.github/workflows/ci.yml` | GitHub Actions | Needs a PR plus a second-account approval |
| Review | CODEOWNERS + branch protection | GitHub | Admin bypass only |

## Lesson learned (why there are three scan points)
A `PreToolUse` hook fires before the command runs. The first commit gate only looked at the git index, so a chained `git add -A && git commit` had nothing staged yet and a PAN-shaped literal in a test file reached a pushed PR; CI's tracked-file scan caught it. Fix: scan the working tree for chained add+commit, scan outgoing commits before push and PR creation, add real git hooks, keep CI as the final backstop. Regression tests: `tests/canary/test_gates.py`.

## Hook behaviour (verified against the Claude Code docs on 2026-11-09)
- Exit code 2 blocks `PreToolUse` and `UserPromptSubmit`, keeps Claude working on `Stop`, and on `PostToolUse` returns stderr to Claude (the tool already ran).
- `UserPromptSubmit` caveat: a blocked prompt is **not erased** from the on-disk transcript by default. DLP-blocked text can therefore still land in a local transcript; treat transcripts as sensitive and keep them on managed devices. Re-check the `suppressOriginalPrompt` option before relying on it.
- Bash deny rules match the literal command only (`Bash(curl *)` misses `/usr/bin/curl`), which is why `guard_bash.py` pattern-matches the command as well.
- `claude -p --bare` skips project hooks. The automated pipeline must not use `--bare`.

## Not yet verified (do not claim in the room)
- Whether `allowManagedHooksOnly` also prevents a developer setting `disableAllHooks`.
- `Skill(...)` permission-rule syntax.
- How to force a specific subagent in non-interactive mode.
