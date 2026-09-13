""".dd/E01/AFF4 container read/write helpers."""

import os


from typing import Optional, Callable


def write_dd_image(
    source_path: str,
    dest_path: str,
    chunk_size: int = 4 * 1024 * 1024,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> int:
    """
    Writes a raw .dd image copy from source_path to dest_path.
    Calls progress_callback(bytes_written, total_source_bytes) if provided.
    Returns the total bytes written.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    total_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0
    total_bytes = 0
    with open(source_path, "rb") as src, open(dest_path, "wb") as dst:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            total_bytes += len(chunk)
            if progress_callback:
                progress_callback(total_bytes, total_size)
    return total_bytes

