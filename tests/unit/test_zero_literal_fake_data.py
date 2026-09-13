"""
Acceptance Test 4: Zero-Literal-Fake-Data Grep Test.
A strict CI guard that scans the entire app/engine9_ui/ codebase and fails if:
1. Any banned legacy hardcoded fake strings (hashes, fake device names, fake case IDs, fake timestamps) appear.
2. Any bare hex string matching the length of MD5 (32-char) or SHA-256 (64-char) appears in any .py file.
3. Any deleted fake seeding methods (_load_synthetic_demo, populate_default_*, etc.) reappear.
"""

import os
import re
import pytest

BANNED_LITERAL_STRINGS = [
    "7f83b165",
    "WD Purple",
    "CR-2026-MH-4019",
    "2023-11-14",
    "HIK_CH1_0001",
    "_load_synthetic_demo",
    "_populate_initial_triage_db",
    "_populate_demo_only_triage_db",
    "populate_default_triage_results",
    "populate_default_journey_matches",
    "Load Synthetic Test Case",
]

# Patterns for bare 64-character (SHA-256) or 32-character (MD5) hex strings
# (Ignoring hex colors like #FFFFFF or 6-digit colors)
SHA256_REGEX = re.compile(r"""['"][0-9a-fA-F]{64}['"]""")
MD5_REGEX = re.compile(r"""['"][0-9a-fA-F]{32}['"]""")


def test_zero_literal_fake_data_in_ui():
    """Scans all Python files in app/engine9_ui for hardcoded mock literals and bare hashes."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ui_dir = os.path.join(base_dir, "app", "engine9_ui")
    assert os.path.isdir(ui_dir), f"UI directory not found: {ui_dir}"

    violations = []

    for root, _, files in os.walk(ui_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            f_path = os.path.join(root, f)
            rel_path = os.path.relpath(f_path, base_dir)

            with open(f_path, "r", encoding="utf-8", errors="ignore") as fh:
                for line_idx, line in enumerate(fh, start=1):
                    # Check banned literal strings
                    for banned in BANNED_LITERAL_STRINGS:
                        if banned in line:
                            violations.append(
                                f"{rel_path}:{line_idx} - Contains banned literal '{banned}': {line.strip()}"
                            )

                    # Check bare SHA-256 literals
                    if SHA256_REGEX.search(line):
                        violations.append(
                            f"{rel_path}:{line_idx} - Contains bare SHA-256 hex literal: {line.strip()}"
                        )

                    # Check bare MD5 literals
                    if MD5_REGEX.search(line):
                        violations.append(
                            f"{rel_path}:{line_idx} - Contains bare MD5 hex literal: {line.strip()}"
                        )

    if violations:
        msg = f"Found {len(violations)} fake data literal violation(s) in app/engine9_ui:\n" + "\n".join(violations)
        pytest.fail(msg)
