"""
Cryptographic key management & hash verification helpers.
"""

import hashlib
import os


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_sha256_file(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def verify_file_hash(file_path: str, expected_hash: str) -> bool:
    if not os.path.exists(file_path):
        return False
    actual_hash = compute_sha256_file(file_path)
    return actual_hash.lower() == expected_hash.lower()
