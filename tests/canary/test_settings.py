"""The policy files must be valid and point at hook scripts that exist."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = json.loads((ROOT / ".claude" / "settings.json").read_text())


def test_every_hook_script_exists() -> None:
    scripts = re.findall(r"hooks/(\w+\.py)", json.dumps(SETTINGS["hooks"]))
    assert scripts
    for name in scripts:
        assert (ROOT / ".claude" / "hooks" / name).is_file(), name


def test_required_events_are_wired() -> None:
    assert {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"} <= set(
        SETTINGS["hooks"]
    )


def test_deny_rules_cover_secrets_network_and_merge() -> None:
    deny = " ".join(SETTINGS["permissions"]["deny"])
    for needle in ("env", "secrets", "curl", "gh pr merge", "--force"):
        assert needle in deny


def test_managed_example_is_valid_json_with_lock_keys() -> None:
    managed = json.loads((ROOT / "docs" / "managed-settings.example.json").read_text())
    assert managed["allowManagedHooksOnly"] is True
    assert managed["allowManagedPermissionRulesOnly"] is True
