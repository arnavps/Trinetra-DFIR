"""Best-effort fallback for OEMs without a dedicated parser — delegates to the Frame Carver rather than claiming structured parsing it can't do."""

import os
from datetime import datetime, timezone
from typing import List

from app.engine3_parsers.fs_base import (
    FileSystemParser,
    VirtualFileSystem,
    ChannelInfo,
    ExtractedFileEntry,
    ClusterRun,
)
from app.engine1_acquisition.image_reader import ImageReader
from app.engine4_carver.frame_carver import carve_nal_units
from app.engine4_carver.gop_reconstructor import reassemble_gop_fragments


class GenericParser(FileSystemParser):
    """Generic fallback parser that routes undetected OEM images to Engine 4 carving."""

    def parse(self, image_path: str) -> VirtualFileSystem:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path '{image_path}' does not exist.")

        with ImageReader(image_path) as f:
            file_size = f.size()
        nal_units = carve_nal_units(image_path)
        gop_fragments = reassemble_gop_fragments(nal_units)

        files: List[ExtractedFileEntry] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        if gop_fragments:
            for idx, gop in enumerate(gop_fragments):
                file_entry = ExtractedFileEntry(
                    file_id=f"CARVED_FRAGMENT_{idx+1:04d}",
                    channel_id=0,
                    start_timestamp=now_iso,
                    end_timestamp=now_iso,
                    size_bytes=len(gop),
                    cluster_runs=[ClusterRun(start_sector=0, sector_count=(len(gop) + 511) // 512)],
                    extraction_type="carved_fragment",
                )
                files.append(file_entry)
        else:
            file_entry = ExtractedFileEntry(
                file_id="CARVED_FRAGMENT_0001",
                channel_id=0,
                start_timestamp=now_iso,
                end_timestamp=now_iso,
                size_bytes=min(file_size, 64 * 1024 * 1024),
                cluster_runs=[ClusterRun(start_sector=0, sector_count=(min(file_size, 64 * 1024 * 1024) + 511) // 512)],
                extraction_type="carved_fragment",
            )
            files.append(file_entry)

        channels = [
            ChannelInfo(
                channel_id=0,
                channel_name="Carved / Best-Effort Channel",
                start_timestamp=now_iso,
                end_timestamp=now_iso,
                total_files=len(files),
            )
        ]

        return VirtualFileSystem(oem="Unknown (Carved / Best-Effort)", channels=channels, files=files)
