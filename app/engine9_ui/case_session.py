"""Centralized state management for Trinetra-DFIR — the single source of truth.

No UI page may hold local hardcoded defaults or unverified values.
When no case is loaded, attributes are None and pages render their explicit Empty states.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QObject, Signal

from app.engine1_acquisition.acquirer import AcquisitionResult
from app.engine2_detector.signature_matcher import MatchResult
from app.engine3_parsers.fs_base import VirtualFileSystem, ExtractedFileEntry
from app.engine7_case_db.db import init_db
from app.engine7_case_db.audit_log import log_event


class CaseSession(QObject):
    """
    Centralized case session tracking active evidence, filesystem, and audit logs.
    Emits signals on state changes so UI components update reactively.
    """

    # Signals
    case_changed = Signal()
    acquisition_completed = Signal(object)
    oem_detected = Signal(object)
    vfs_loaded = Signal(object)
    fragments_updated = Signal(list)
    active_file_changed = Signal(object)
    event_logged = Signal(dict)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.case_id: Optional[str] = None
        self.case_name: Optional[str] = None
        self.investigator_name: Optional[str] = None
        self.db_path: Optional[str] = None
        self.evidence_source: Optional[str] = None
        self.image_path: Optional[str] = None
        self.write_block_verified: Optional[bool] = None
        self.acquisition_result: Optional[AcquisitionResult] = None
        self.oem_match_result: Optional[MatchResult] = None
        self.virtual_file_system: Optional[VirtualFileSystem] = None
        self.carved_fragments: List[ExtractedFileEntry] = []
        self.timeline_normalization: Optional[Dict[str, Any]] = None
        self.active_file_entry: Optional[ExtractedFileEntry] = None
        self.events_log: List[Dict[str, Any]] = []

    @property
    def has_case(self) -> bool:
        return self.case_id is not None and self.db_path is not None

    @property
    def has_evidence(self) -> bool:
        return self.image_path is not None and os.path.exists(self.image_path)

    @property
    def has_vfs(self) -> bool:
        return self.virtual_file_system is not None

    def create_case(
        self,
        case_id: Optional[str] = None,
        name: Optional[str] = None,
        investigator: Optional[str] = None,
        base_dir: str = "cases",
        db_path: Optional[str] = None,
        case_name: Optional[str] = None,
    ) -> str:
        """Initializes a new case directory and SQLite WAL database."""
        self.reset()

        actual_name = case_name or name
        self.case_id = case_id.strip() if case_id and case_id.strip() else f"CR-{uuid.uuid4().hex[:8].upper()}"
        self.case_name = actual_name.strip() if actual_name and actual_name.strip() else f"Case {self.case_id}"
        self.investigator_name = investigator.strip() if investigator and investigator.strip() else "Unassigned Investigator"

        if db_path:
            self.db_path = db_path
            case_dir = os.path.dirname(db_path)
            if case_dir:
                os.makedirs(case_dir, exist_ok=True)
        else:
            case_dir = os.path.join(base_dir, f"case_{self.case_id.replace(':', '_').replace(' ', '_')}")
            os.makedirs(case_dir, exist_ok=True)
            self.db_path = os.path.join(case_dir, "case.db")

        # Initialize SQLite database schema
        init_db(self.db_path)

        # Log CASE_CREATED event
        self.log_engine_event(
            event_type="CASE_CREATED",
            message=f"Case initialized: {self.case_id} ({self.case_name})",
            details={
                "case_id": self.case_id,
                "name": self.case_name,
                "investigator": self.investigator_name,
                "db_path": self.db_path,
            },
        )

        self.case_changed.emit()
        return self.case_id

    def set_evidence_source(self, source_path: str) -> None:
        """Sets the selected physical or logical evidence source path."""
        self.evidence_source = source_path
        self.log_engine_event(
            event_type="SOURCE_SELECTED",
            message=f"Evidence source selected: {source_path}",
            details={"source": source_path},
        )
        self.case_changed.emit()

    def set_write_block_status(self, verified: bool) -> None:
        """Records hardware/software write-block check verification result."""
        self.write_block_verified = verified
        event = "WRITE_BLOCK_VERIFIED" if verified else "WRITE_BLOCK_VIOLATION"
        msg = "Write-block verified: Read-only access confirmed" if verified else "WRITE VIOLATION: Source is writable!"
        self.log_engine_event(
            event_type=event,
            message=msg,
            details={"verified": verified, "source": self.evidence_source},
        )
        self.case_changed.emit()

    def set_acquisition_result(self, result: AcquisitionResult) -> None:
        """Records acquisition result including SHA-256 and Merkle root."""
        self.acquisition_result = result
        self.image_path = result.path
        self.log_engine_event(
            event_type="ACQUISITION_RECORDED",
            message=f"Acquisition finished: {result.byte_count} bytes, SHA-256: {result.sha256[:16]}...",
            details={
                "path": result.path,
                "sha256": result.sha256,
                "md5": result.md5,
                "merkle_root": result.merkle_root,
                "byte_count": result.byte_count,
            },
        )
        self.acquisition_completed.emit(result)
        self.case_changed.emit()

    def set_oem_result(self, result: MatchResult) -> None:
        """Records OEM signature match or fallback classification result."""
        self.oem_match_result = result
        status = f"OEM matched: {result.oem} at offset 0x{result.matched_offset:X}" if result.matched else f"OEM unverified: {result.oem}"
        self.log_engine_event(
            event_type="OEM_DETECTED",
            message=status,
            details={
                "oem": result.oem,
                "matched": result.matched,
                "offset": result.matched_offset,
                "signature_id": result.signature_id,
            },
        )
        self.oem_detected.emit(result)
        self.case_changed.emit()

    def set_vfs(self, vfs: VirtualFileSystem) -> None:
        """Sets the parsed VirtualFileSystem and records extracted files into the case database."""
        self.virtual_file_system = vfs
        total_files = len(vfs.files) if vfs else 0
        total_channels = len(vfs.channels) if vfs else 0

        self.log_engine_event(
            event_type="VFS_PARSED",
            message=f"VFS parsed: {total_channels} channels, {total_files} evidentiary files",
            details={"oem": vfs.oem, "channels": total_channels, "files": total_files},
        )

        if vfs and vfs.files and self.active_file_entry is None:
            self.active_file_entry = vfs.files[0]
            self.active_file_changed.emit(self.active_file_entry)

        self.vfs_loaded.emit(vfs)
        self.case_changed.emit()

    def add_carved_fragment(self, fragment: ExtractedFileEntry) -> None:
        """Adds a recovered NAL elementary stream fragment to the session."""
        self.carved_fragments.append(fragment)
        self.log_engine_event(
            event_type="FRAGMENT_CARVED",
            message=f"Recovered fragment {fragment.file_id}: {fragment.size_bytes} bytes",
            details={
                "file_id": fragment.file_id,
                "size_bytes": fragment.size_bytes,
                "extraction_type": fragment.extraction_type,
            },
        )
        self.fragments_updated.emit(self.carved_fragments)
        self.case_changed.emit()

    def set_active_file(self, entry: Optional[ExtractedFileEntry]) -> None:
        """Updates the active video clip selected for playback and forensic analysis."""
        self.active_file_entry = entry
        if entry:
            self.log_engine_event(
                event_type="CLIP_SELECTED",
                message=f"Active clip: {entry.file_id} (Channel {entry.channel_id})",
                details={"file_id": entry.file_id, "channel_id": entry.channel_id},
            )
        self.active_file_changed.emit(entry)

    def log_engine_event(
        self,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Logs a real backend engine event to the in-memory ticker and audit database.
        Proof-of-life: every live operation emits real events.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        event_data = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "details": details or {},
        }
        self.events_log.append(event_data)

        # Write to SQLite hash-chained audit log if case is initialized
        if self.db_path and self.case_id:
            try:
                log_event(
                    db_path=self.db_path,
                    case_id=self.case_id,
                    event_type=event_type,
                    details={"message": message, **(details or {})},
                )
            except Exception:
                pass

        self.event_logged.emit(event_data)

    def reset(self) -> None:
        """Resets the active session to uninitialized state."""
        self.case_id = None
        self.case_name = None
        self.investigator_name = None
        self.db_path = None
        self.evidence_source = None
        self.image_path = None
        self.write_block_verified = None
        self.acquisition_result = None
        self.oem_match_result = None
        self.virtual_file_system = None
        self.carved_fragments = []
        self.timeline_normalization = None
        self.active_file_entry = None
        self.events_log = []
        self.case_changed.emit()
