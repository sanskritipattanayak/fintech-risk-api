"""Regression tests: a canary must be stopped BEFORE commit, push and PR creation.

Background: the first commit gate scanned the index when the hook fired, but a chained
`git add ... && git commit` has not staged anything yet at that moment, so a PAN literal
slipped through to a pushed PR. These tests pin the fixed behaviour at three layers:
the Claude PreToolUse hook, real git hooks, and (separately) CI.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tests.canary import canaries

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
# Drop inherited GIT_* (e.g. GIT_DIR exported to hooks) so scratch repos never touch this one.
GIT_ENV = {
    **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.test",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.test",
}


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, env=GIT_ENV, check=check
    )


def make_repo(tmp_path: Path) -> Path:
    """A repo on `main` with one clean commit and an `origin/main` ref."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("clean\n")
    git(repo, "add", "README.md")
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "init")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "-q", "-b", "feat/x")
    return repo


def guard(repo: Path, command: str) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = {**GIT_ENV, "CLAUDE_PROJECT_DIR": str(repo)}
    return subprocess.run(
        [sys.executable, str(HOOKS / "guard_bash.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=repo,
        env=env,
    )


def commit_canary_bypassing_gates(repo: Path) -> None:
    (repo / "fixture.csv").write_text(canaries.FIXTURE_ROW + "\n")
    git(repo, "add", "fixture.csv")
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "sneaky")


def test_scratch_repos_ignore_inherited_git_dir(tmp_path: Path) -> None:
    # Git exports GIT_DIR to hooks. When pre-push ran this suite, make_repo's `git init`
    # re-initialised the real repository as bare. A decoy worktree stands in for it here.
    (tmp_path / "decoy_main").mkdir()
    decoy = make_repo(tmp_path / "decoy_main")
    git(decoy, "worktree", "add", "-q", str(tmp_path / "decoy"), "-b", "wt")
    decoy = tmp_path / "decoy"
    refs_before = git(decoy, "for-each-ref").stdout
    gitdir = git(decoy, "rev-parse", "--absolute-git-dir").stdout.strip()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    code = (
        "from pathlib import Path; from tests.canary.test_gates import make_repo; "
        f"make_repo(Path({str(scratch)!r}))"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**env, "GIT_DIR": gitdir},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr[-500:]
    assert git(decoy, "config", "--get", "core.bare").stdout.strip() == "false"
    assert git(decoy, "for-each-ref").stdout == refs_before


# ---- Claude PreToolUse layer ---------------------------------------------------------


def test_chained_add_and_commit_is_scanned(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "fixture.csv").write_text(canaries.FIXTURE_ROW + "\n")  # untracked, not staged
    r = guard(repo, 'git add -A && git commit -m "add fixture"')
    assert r.returncode == 2 and "commit-dlp" in r.stderr
    assert canaries.PAN not in r.stderr


def test_commit_all_flag_is_scanned(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "README.md").write_text(canaries.FIXTURE_ROW + "\n")  # tracked, modified, unstaged
    r = guard(repo, 'git commit -am "update readme"')
    assert r.returncode == 2 and "commit-dlp" in r.stderr


def test_push_scans_outgoing_commits(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_canary_bypassing_gates(repo)
    r = guard(repo, "git push origin feat/x")
    assert r.returncode == 2 and "push-dlp" in r.stderr


def test_pr_create_scans_outgoing_commits(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    commit_canary_bypassing_gates(repo)
    r = guard(repo, 'gh pr create --title "x" --body "y"')
    assert r.returncode == 2 and "pr-dlp" in r.stderr


def test_commit_then_push_chain_is_scanned(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "fixture.csv").write_text(canaries.FIXTURE_ROW + "\n")
    r = guard(repo, "git add -A && git commit -m x && git push origin feat/x")
    assert r.returncode == 2


def test_clean_changes_pass_every_gate(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "notes.md").write_text("synthetic only, card_0a1b2c3d\n")
    assert guard(repo, 'git add -A && git commit -m "notes"').returncode == 0
    assert guard(repo, "git push origin feat/x").returncode == 0
    assert guard(repo, 'gh pr create --title "x" --body "y"').returncode == 0


# ---- real git hooks (cannot be skipped by how the command is phrased) --------------


def install_git_hooks(repo: Path) -> None:
    shutil.copytree(ROOT / ".githooks", repo / ".githooks")
    shutil.copytree(HOOKS, repo / ".claude" / "hooks", ignore=shutil.ignore_patterns("__pycache__"))
    git(repo, "config", "core.hooksPath", ".githooks")


def test_git_pre_commit_blocks_canary(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    install_git_hooks(repo)
    (repo / "fixture.csv").write_text(canaries.FIXTURE_ROW + "\n")
    git(repo, "add", "fixture.csv")
    r = git(repo, "commit", "-q", "-m", "x", check=False)
    assert r.returncode != 0 and "DATA_CHECK: FAIL" in r.stdout + r.stderr
    assert canaries.PAN not in r.stdout + r.stderr


def test_git_pre_push_blocks_canary_even_if_commit_hook_was_skipped(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    install_git_hooks(repo)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    commit_canary_bypassing_gates(repo)
    r = git(repo, "push", "origin", "HEAD", check=False)
    assert r.returncode != 0 and "DATA_CHECK: FAIL" in r.stdout + r.stderr
    assert not list((remote / "refs" / "heads").glob("*")), "canary reached the remote"
