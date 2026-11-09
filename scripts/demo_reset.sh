#!/usr/bin/env bash
# Repeatable demo runs. Every run happens in a throwaway git worktree cut from the
# `demo-start` tag, so your real checkout is never touched and a reset is exact.
#
#   scripts/demo_reset.sh start [INCIDENT_ID]   create the demo worktree on fix/<id>
#   scripts/demo_reset.sh reset [INCIDENT_ID]   destroy it (worktree, local fix branch, run outputs)
#   scripts/demo_reset.sh status
#
# Run this yourself in a terminal. It is deliberately not something to hand to the agent:
# `reset` deletes things, and the harness asks a human before deletes and history rewrites.
# It never pushes, never touches remotes, never touches main or the demo-start tag.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${DEMO_TAG:-demo-start}"
ACTION="${1:-status}"
ID="${2:-INC-DEMO-001}"
BRANCH="fix/${ID}"
WT="${DEMO_DIR:-$(dirname "$ROOT")/fintech-risk-demo-run}"
cd "$ROOT"

have_tag() { git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; }

case "$ACTION" in
  start)
    have_tag || { echo "Tag ${TAG} not found. Merge the Phase 5 PR, then: git tag ${TAG} <main sha>"; exit 1; }
    [[ -e "$WT" ]] && { echo "${WT} exists. Run: scripts/demo_reset.sh reset ${ID}"; exit 1; }
    git worktree add -b "$BRANCH" "$WT" "$TAG"
    [[ -d "$ROOT/.venv" ]] && ln -s "$ROOT/.venv" "$WT/.venv"
    echo
    echo "Demo worktree ready on ${BRANCH} (from ${TAG}): ${WT}"
    echo "  cd ${WT} && claude        # interactive, hooks live"
    echo "  cd ${WT} && scripts/log_to_fix.sh ${ID}   # headless"
    echo "Check the starting state: .venv/bin/pytest -q  (expect 1 xfailed)"
    ;;
  reset)
    echo "This will remove: worktree ${WT}, local branch ${BRANCH}."
    read -r -p "Proceed? [y/N] " ans; [[ "$ans" == "y" ]] || exit 0
    [[ -e "$WT" ]] && git worktree remove --force "$WT"
    git worktree prune
    git show-ref --verify --quiet "refs/heads/${BRANCH}" && git branch -D "$BRANCH"
    echo "Reset. Remote branches and any open PR are untouched: close the PR and delete"
    echo "the remote ${BRANCH} on GitHub yourself if you pushed one."
    echo "Run: scripts/demo_reset.sh start ${ID}"
    ;;
  status)
    have_tag && echo "tag ${TAG}: $(git rev-parse --short "${TAG}")" || echo "tag ${TAG}: missing"
    [[ -e "$WT" ]] && echo "worktree: ${WT}" || echo "worktree: none"
    git show-ref --verify --quiet "refs/heads/${BRANCH}" && echo "branch ${BRANCH}: present" || echo "branch ${BRANCH}: none"
    ;;
  *) echo "usage: $0 start|reset|status [INCIDENT_ID]"; exit 2 ;;
esac
