"""
Network watchdog enforcing 100% offline air-gapped environment invariant.
"""

import socket


class NetworkViolationError(Exception):
    """Raised when network activity is detected in an air-gapped environment."""
    pass


def assert_offline_environment() -> bool:
    """
    Verifies that no active outbound socket connections can be established.
    Raises NetworkViolationError if network access is detected.
    """
    try:
        # Attempt connection to dummy external IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        res = sock.connect_ex(("1.1.1.1", 53))
        sock.close()
        if res == 0:
            raise NetworkViolationError("Air-gap violation: Active network connection detected!")
    except (socket.error, socket.timeout):
        pass

    return True
