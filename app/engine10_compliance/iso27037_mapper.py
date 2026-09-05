"""
Maps logged case events onto the four ISO/IEC 27037 phases (Blueprint §5.1):
1. Identification
2. Collection
3. Acquisition
4. Preservation
"""

from typing import List, Dict, Any


def map_case_to_iso27037(audit_log_entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorizes audit log entries into the 4 standard ISO/IEC 27037 digital evidence handling phases.
    """
    mapped_phases: Dict[str, List[Dict[str, Any]]] = {
        "Identification": [],
        "Collection": [],
        "Acquisition": [],
        "Preservation": [],
    }

    for entry in audit_log_entries:
        event_type = entry.get("event_type", "").lower()
        
        if "case_create" in event_type or "identify" in event_type or "detect" in event_type:
            mapped_phases["Identification"].append(entry)
        elif "acquisition" in event_type or "image" in event_type or "raw_read" in event_type:
            mapped_phases["Acquisition"].append(entry)
        elif "parse" in event_type or "carve" in event_type or "collect" in event_type or "extract" in event_type:
            mapped_phases["Collection"].append(entry)
        else:
            # Audit hashing, verification, exports, reports, and normalizations map to Preservation
            mapped_phases["Preservation"].append(entry)

    return mapped_phases
