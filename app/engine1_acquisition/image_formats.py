""".dd/E01/AFF4 container read/write helpers."""

import os


def write_dd_image(source_path: str, dest_path: str, chunk_size: int = 4 * 1024 * 1024) -> int:
    """
    Writes a raw .dd image copy from source_path to dest_path.
    Returns the total bytes written.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    total_bytes = 0
    with open(source_path, "rb") as src, open(dest_path, "wb") as dst:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            total_bytes += len(chunk)
    return total_bytes
