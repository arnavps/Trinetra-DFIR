"""Verifies the source handle is opened read-only before acquirer.py is allowed to proceed; hard-errors otherwise."""

import os
import stat


class WriteBlockViolationError(PermissionError):
    """Raised when a source handle or path is opened or accessible in writable mode."""
    pass


def verify_read_only(source_path: str) -> bool:
    """
    Verifies that the source path is opened in strictly read-only mode.
    Attempts to open the file with write permissions. If writable access succeeds,
    raises WriteBlockViolationError.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source path '{source_path}' does not exist.")

    # Attempt to open file with write access
    try:
        with open(source_path, "r+b"):
            raise WriteBlockViolationError(
                f"WRITE-BLOCK VIOLATION: Source path '{source_path}' is accessible in writable mode."
            )
    except WriteBlockViolationError:
        raise
    except (PermissionError, OSError):
        # Open in writable mode failed (as expected for write-blocked source)
        pass

    # Ensure source can be opened read-only
    try:
        with open(source_path, "rb") as f:
            f.read(1)
    except Exception as e:
        raise WriteBlockViolationError(f"Source path '{source_path}' cannot be read: {e}")

    return True
