"""Constants and byte struct definitions for Hikvision HIKFAT filesystem.

NOTE: Per CLAUDE.md invariants, all byte offsets and struct layouts below are
literature-derived placeholders from published reverse-engineering literature
and MUST be verified against a physical acquired drive once available.
"""

# HIKFAT Superblock offset (literature-derived placeholder, unverified on physical hardware)
HIKFAT_SUPERBLOCK_OFFSET = 0
HIKFAT_SUPERBLOCK_MAGIC = b"HIKVISION"

# Master Index Table location (literature-derived placeholder, unverified on physical hardware)
# Index table header lives at file_size - HIKFAT_INDEX_TABLE_OFFSET_FROM_END
HIKFAT_INDEX_TABLE_OFFSET_FROM_END = 4096
HIKFAT_INDEX_MAGIC = b"HIKINDEX"

# Index record binary layout (literature-derived placeholder, unverified on physical hardware)
# Struct format:
# uint16 channel_id
# uint32 start_time (epoch timestamp)
# uint32 end_time (epoch timestamp)
# uint32 start_sector
# uint32 sector_count
# uint64 file_size
HIKFAT_INDEX_RECORD_SIZE = 26
HIKFAT_INDEX_RECORD_STRUCT = "<HIIIIQ"
