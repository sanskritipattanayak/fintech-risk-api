#!/usr/bin/env python3
"""UserPromptSubmit: block prompts that contain restricted data (PAN, SSN, keys...)."""

from __future__ import annotations

import dlp
from common import deny, read_input


def main() -> None:
    prompt = read_input().get("prompt", "")
    findings = dlp.scan_text(prompt)
    if findings:
        deny(
            "UserPromptSubmit",
            "prompt-dlp",
            f"prompt contains restricted data ({dlp.summarize(findings)}). "
            "Remove it or replace it with a token, then resubmit.",
            "prompt",
            prompt,
        )


if __name__ == "__main__":
    main()
