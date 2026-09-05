"""Constants and byte struct definitions for Dahua/CP Plus DHFS filesystem.

NOTE: Per CLAUDE.md invariants, all byte offsets and struct layouts below are
literature-derived placeholders from published reverse-engineering literature
and MUST be verified against a physical acquired drive once available.
"""

# DHFS Superblock offset (literature-derived placeholder, unverified on physical hardware)
DHFS_SUPERBLOCK_OFFSET = 0
DHFS_SUPERBLOCK_MAGIC = b"DHFS"

# Master Index Table location (literature-derived placeholder, unverified on physical hardware)
# Index table header lives at file_size - DHFS_INDEX_TABLE_OFFSET_FROM_END
DHFS_INDEX_TABLE_OFFSET_FROM_END = 4096
DHFS_INDEX_MAGIC = b"DHINDEX"

# Index record binary layout (literature-derived placeholder, unverified on physical hardware)
# Struct format:
# uint16 channel_id
# uint32 start_time (epoch timestamp)
# uint32 end_time (epoch timestamp)
# uint32 start_sector
# uint32 sector_count
# uint64 file_size
DHFS_INDEX_RECORD_SIZE = 26
DHFS_INDEX_RECORD_STRUCT = "<HIIIIQ"
