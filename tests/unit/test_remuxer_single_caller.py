"""Static analysis test enforcing that remuxer.py is ONLY imported/called by export_module.py."""

import os
import re


def test_remuxer_single_caller_invariant():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    app_dir = os.path.join(root_dir, "app")

    allowed_importers = {
        os.path.abspath(os.path.join(app_dir, "engine5_playback", "remuxer.py")),
        os.path.abspath(os.path.join(app_dir, "engine9_ui", "export_module.py")),
    }

    import_pattern = re.compile(r"(import.*remuxer|from.*remuxer.*import)")
    violations = []

    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.abspath(os.path.join(root, file))
                if full_path in allowed_importers:
                    continue

                with open(full_path, "r", encoding="utf-8") as f:
                    for line_no, line in enumerate(f, 1):
                        if import_pattern.search(line):
                            violations.append(f"{full_path}:{line_no} - {line.strip()}")

    assert len(violations) == 0, (
        f"INVARIANT VIOLATION: remuxer.py must ONLY be called by export_module.py!\n"
        f"Found unauthorized imports:\n" + "\n".join(violations)
    )
