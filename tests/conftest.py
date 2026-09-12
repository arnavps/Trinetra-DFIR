"""Pytest global configuration: configures headless Qt environment for CI."""

import os
import pytest

# Ensure PySide6 tests run headlessly in CI/headless environments without requiring an active display server
os.environ["QT_QPA_PLATFORM"] = "offscreen"
