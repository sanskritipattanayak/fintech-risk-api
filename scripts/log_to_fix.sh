#!/usr/bin/env bash
# Flow 2, headless: log alert -> triage -> (G4 check) -> fix branch ready for human ship.
#
# Runs `claude -p` WITHOUT --bare so the project hooks (path policy, DLP, command policy,
# audit log) still fire. Every stage has a tool allow-list and a dollar cap. The script
# stops before commit/push/PR: secure-ship and the human G3/G5 gates own that.
#
# Usage: scripts/log_to_fix.sh [INCIDENT_ID]        (default INC-DEMO-001)
# Env:   TRIAGE_MODEL (haiku)  FIX_MODEL (sonnet)  TRIAGE_BUDGET (0.50)  FIX_BUDGET (1.50)
#        AUTO_CONTINUE=1 skips the human prompt between stages (rehearsal only)
#        CLAUDE_MAX_TURNS  optional; passed as --max-turns only if set (unverified, see README)
set -euo pipefail
cd "$(dirname "$0")/.."

ID="${1:-INC-DEMO-001}"
TRIAGE_MODEL="${TRIAGE_MODEL:-haiku}"
FIX_MODEL="${FIX_MODEL:-sonnet}"
TRIAGE_BUDGET="${TRIAGE_BUDGET:-0.50}"
FIX_BUDGET="${FIX_BUDGET:-1.50}"
REPORT="incidents/${ID}.md"
RUNS=".claude/audit/runs"
mkdir -p "$RUNS" incidents
turns=()
if [[ -n "${CLAUDE_MAX_TURNS:-}" ]]; then turns=(--max-turns "$CLAUDE_MAX_TURNS"); fi

echo "== Stage 1: log-triage (${TRIAGE_MODEL}, cap \$${TRIAGE_BUDGET}) =="
claude -p "Use the log-triage skill on logs/app.log. Write the redacted incident report to ${REPORT} with an 'auto_fix_eligible: true|false' line. Do not edit source." \
  --model "$TRIAGE_MODEL" \
  --allowedTools "Read(logs/*)" "Grep" "Glob" "Edit(incidents/*)" "Write(incidents/*)" "Skill(log-triage)" "Skill(fintech-data-check)" "Bash(git log *)" \
  --max-budget-usd "$TRIAGE_BUDGET" ${turns[@]+"${turns[@]}"} \
  --output-format json > "$RUNS/${ID}.triage.json"

echo "== Gate G4: eligibility =="
if [[ ! -f "$REPORT" ]]; then echo "No incident report written; stopping."; exit 2; fi
if ! grep -qiE '^\W*auto_fix_eligible\W*:\s*true' "$REPORT"; then
  echo "G4: not auto-fix eligible. Page on-call with ${REPORT}. Pipeline stops here."; exit 3
fi
echo "G4: eligible. Report: ${REPORT}"
if [[ "${AUTO_CONTINUE:-}" != "1" ]]; then
  read -r -p "Proceed to stage 2 (fix)? [y/N] " ans; [[ "$ans" == "y" ]] || exit 0
fi

echo "== Stage 2: bugfix-pr (${FIX_MODEL}, cap \$${FIX_BUDGET}) =="
claude -p "Use the bugfix-pr skill on ${REPORT}. Branch fix/${ID}. Write the failing regression test first, then the minimal fix. Stop before commit: do not run secure-ship, do not push." \
  --model "$FIX_MODEL" \
  --allowedTools "Read" "Grep" "Glob" "Edit(app/*)" "Edit(tests/*)" "Write(tests/*)" "Bash(pytest *)" "Bash(ruff *)" "Bash(git checkout -b fix/*)" "Bash(git diff *)" "Bash(git status *)" "Skill(bugfix-pr)" "Skill(fintech-data-check)" \
  --max-budget-usd "$FIX_BUDGET" ${turns[@]+"${turns[@]}"} \
  --output-format json > "$RUNS/${ID}.fix.json"

echo "== Done. Branch fix/${ID} holds an uncommitted fix + regression test. =="
echo "Next (human, interactive): review 'git diff', run the secure-ship skill (G3), then PR review (G5)."
