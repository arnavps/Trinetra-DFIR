"""Abstract FileSystemParser interface (parse(image_reader) -> VirtualFileSystem) every OEM plugin implements; keeps parsers swappable and independently testable."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClusterRun:
    start_sector: int
    sector_count: int


@dataclass
class ExtractedFileEntry:
    file_id: str
    channel_id: int
    start_timestamp: str
    end_timestamp: str
    size_bytes: int
    cluster_runs: List[ClusterRun] = field(default_factory=list)
    extraction_type: str = "parsed"


@dataclass
class ChannelInfo:
    channel_id: int
    channel_name: str
    start_timestamp: Optional[str]
    end_timestamp: Optional[str]
    total_files: int


@dataclass
class VirtualFileSystem:
    oem: str
    channels: List[ChannelInfo] = field(default_factory=list)
    files: List[ExtractedFileEntry] = field(default_factory=list)


class FileSystemParser(ABC):
    """Abstract interface for all OEM filesystem parsers."""

    @abstractmethod
    def parse(self, image_path: str) -> VirtualFileSystem:
        """
        Parses an acquired drive image read-only and returns a VirtualFileSystem structure.
        Must be implemented by every OEM parser plugin.
        """
        pass
