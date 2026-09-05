"""Dahua/CP Plus DHFS parser — locates end-of-drive index tables, maps channel/time allocation. Byte offsets live in a separate constants block, seeded from published literature and corrected against real drives as they're imaged."""

import os
import struct
from datetime import datetime, timezone
from typing import Dict, List

from app.engine3_parsers.fs_base import (
    FileSystemParser,
    VirtualFileSystem,
    ChannelInfo,
    ExtractedFileEntry,
    ClusterRun,
)
from app.engine3_parsers import dhfs_constants as const


class DhfsParser(FileSystemParser):
    """Dahua / CP Plus DHFS filesystem parser implementation."""

    def parse(self, image_path: str) -> VirtualFileSystem:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path '{image_path}' does not exist.")

        with open(image_path, "rb") as f:
            file_size = f.seek(0, os.SEEK_END)

            # 1. Verify Superblock Magic
            if file_size < len(const.DHFS_SUPERBLOCK_MAGIC):
                raise ValueError("Image file too small to contain Dahua superblock.")

            f.seek(const.DHFS_SUPERBLOCK_OFFSET)
            superblock_magic = f.read(len(const.DHFS_SUPERBLOCK_MAGIC))
            if superblock_magic != const.DHFS_SUPERBLOCK_MAGIC:
                raise ValueError(f"Invalid DHFS superblock signature: {superblock_magic}")

            # 2. Locate Index Table
            index_offset = file_size - const.DHFS_INDEX_TABLE_OFFSET_FROM_END
            if index_offset < 0:
                raise ValueError("Image file size smaller than DHFS index table offset.")

            f.seek(index_offset)
            index_magic = f.read(len(const.DHFS_INDEX_MAGIC))
            if index_magic != const.DHFS_INDEX_MAGIC:
                raise ValueError(f"Invalid DHFS index table signature: {index_magic}")

            # Read record count
            record_count_bytes = f.read(2)
            if len(record_count_bytes) < 2:
                record_count = 0
            else:
                record_count = struct.unpack("<H", record_count_bytes)[0]

            files: List[ExtractedFileEntry] = []
            channels_map: Dict[int, List[ExtractedFileEntry]] = {}

            for idx in range(record_count):
                record_bytes = f.read(const.DHFS_INDEX_RECORD_SIZE)
                if len(record_bytes) < const.DHFS_INDEX_RECORD_SIZE:
                    break

                channel_id, start_ts, end_ts, start_sec, sec_count, fsize = struct.unpack(
                    const.DHFS_INDEX_RECORD_STRUCT, record_bytes
                )

                start_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat()
                end_iso = datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat()

                entry = ExtractedFileEntry(
                    file_id=f"DH_CH{channel_id}_{idx+1:04d}",
                    channel_id=channel_id,
                    start_timestamp=start_iso,
                    end_timestamp=end_iso,
                    size_bytes=fsize,
                    cluster_runs=[ClusterRun(start_sector=start_sec, sector_count=sec_count)],
                    extraction_type="parsed",
                )

                files.append(entry)

                if channel_id not in channels_map:
                    channels_map[channel_id] = []
                channels_map[channel_id].append(entry)

            # Build ChannelInfo list
            channels: List[ChannelInfo] = []
            for ch_id, ch_files in sorted(channels_map.items()):
                start_timestamps = [f.start_timestamp for f in ch_files]
                end_timestamps = [f.end_timestamp for f in ch_files]
                channels.append(
                    ChannelInfo(
                        channel_id=ch_id,
                        channel_name=f"Camera {ch_id}",
                        start_timestamp=min(start_timestamps) if start_timestamps else None,
                        end_timestamp=max(end_timestamps) if end_timestamps else None,
                        total_files=len(ch_files),
                    )
                )

            return VirtualFileSystem(oem="Dahua", channels=channels, files=files)
